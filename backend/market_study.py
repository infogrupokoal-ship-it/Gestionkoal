import json
import os
import random
import time

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from googleapiclient.discovery import build

from backend.auth import login_required
from backend.db import get_db
from backend.forms import get_material_choices  # New imports

bp = Blueprint('market_study', __name__, url_prefix='/market_study')

def _perform_web_search(query):
    """
    Performs a web search using Google Custom Search API.
    """
    api_key = os.environ.get("GOOGLE_API_KEY")
    cse_id = os.environ.get("GOOGLE_CSE_ID")

    if not api_key or not cse_id:
        current_app.logger.warning("GOOGLE_API_KEY or GOOGLE_CSE_ID not set. Using mock web search.")
        return _perform_mock_web_search(query)

    try:
        service = build("customsearch", "v1", developerKey=api_key)
        res = service.cse().list(q=query, cx=cse_id, num=5).execute() # num=5 for 5 results

        results = []
        if 'items' in res:
            for item in res['items']:
                results.append({
                    "title": item.get('title'),
                    "url": item.get('link'),
                    "snippet": item.get('snippet')
                })
        return results
    except Exception as e:
        current_app.logger.error(f"Error performing web search with Custom Search API: {e}")
        return _perform_mock_web_search(query) # Fallback to mock search on error

def _perform_mock_web_search(query):
    """
    Mocks a web search for demonstration purposes.
    Used as a fallback if Custom Search API fails or is not configured.
    """
    time.sleep(1) # Simulate network delay
    results = []
    for i in range(random.randint(3, 7)):
        results.append({
            "title": f"Mock Result {i+1} for {query}",
            "url": f"http://mocksearch.com/result{i+1}?q={query}",
            "snippet": f"This is a mock snippet for result {i+1} related to {query}. It contains some relevant information."
        })
    return results

def _calculate_difficulty(price_avg, num_sources):
    """
    Calculates a mock difficulty level based on average price and number of sources.
    """
    if price_avg is None or num_sources == 0:
        return 'unknown'

    if price_avg < 50 and num_sources > 5:
        return 'easy'
    elif price_avg < 200 and num_sources > 3:
        return 'medium'
    else:
        return 'hard'

def get_market_study_for_material_helper(material_id):
    db = get_db()
    if db is None:
        current_app.logger.error("Database connection error in get_market_study_for_material.")
        return None

    # ... rest of the function

# --- Helper Functions for Market Study ---
from typing import Any

def get_current_workload():
    db = get_db()
    # Count jobs that are not 'completado' or 'cancelado'
    cursor = db.execute(
        "SELECT COUNT(id) AS active_jobs FROM tickets WHERE estado NOT IN ('completado', 'cancelado')"
    )
    active_jobs = cursor.fetchone()['active_jobs']
    return active_jobs


def calculate_difficulty(price_data: list[dict[str, Any]]) -> str:
    """
    Calcula el nivel de dificultad basado en la disponibilidad y variación de precios.
    price_data: lista de diccionarios con {price, availability}
    """
    if not price_data:
        return 'dificil' # No data, assume difficult

    available_sources = [p for p in price_data if p.get('availability') != 'no_stock']
    if len(available_sources) < 2:
        return 'dificil' # Less than 2 available sources

    prices = [p['price'] for p in available_sources if p.get('price') is not None]
    if len(prices) < 2:
        return 'dificil' # Not enough prices to compare

    # Simple variance check (more sophisticated could be std dev)
    min_price = min(prices)
    max_price = max(prices)
    if min_price == 0:
        return 'dificil' # Avoid division by zero

    price_variation = (max_price - min_price) / min_price

    if len(available_sources) > 3 and price_variation < 0.15: # Low variation
        return 'facil'
    elif len(available_sources) >= 2 and price_variation < 0.40: # Moderate variation
        return 'medio'
    else:
        return 'dificil'

def mock_web_search(material_name: str, sector: str) -> dict:
    """
    Simula una búsqueda web para obtener precios y fuentes.
    En un entorno real, esto usaría APIs de scraping o de proveedores.
    """
    current_app.logger.info(f"Simulating web search for: {material_name} in sector {sector}")

    # Example mock data
    mock_results = {
        "Tornillos Estrella 4x40": [
            {"source": "FerreteriaOnline.es", "price": 5.20, "date": "2025-09-29", "availability": "in_stock"},
            {"source": "BricoDepot.es", "price": 5.80, "date": "2025-09-28", "availability": "in_stock"},
            {"source": "Amazon.es", "price": 6.10, "date": "2025-09-29", "availability": "in_stock"},
        ],
        "Cable 2.5mm Negro": [
            {"source": "ElectricidadExpress.com", "price": 0.70, "date": "2025-09-29", "availability": "in_stock"},
            {"source": "LeroyMerlin.es", "price": 0.85, "date": "2025-09-28", "availability": "in_stock"},
        ],
        "Cinta de teflón": [
            {"source": "FontaneriaPro.es", "price": 1.10, "date": "2025-09-29", "availability": "in_stock"},
        ],
        "Rodillo de espuma": [
            {"source": "PinturasOnline.es", "price": 3.40, "date": "2025-09-29", "availability": "no_stock"},
            {"source": "BricoMark.es", "price": 3.60, "date": "2025-09-28", "availability": "in_stock"},
        ],
    }

    results = mock_results.get(material_name, [])

    if not results:
        return {"price_avg": None, "price_min": None, "price_max": None, "sources_json": "[]", "difficulty": "dificil"}

    prices = [r['price'] for r in results if r.get('price') is not None]
    price_avg = sum(prices) / len(prices) if prices else None
    price_min = min(prices) if prices else None
    price_max = max(prices) if prices else None

    difficulty = calculate_difficulty(results)

    return {
        "price_avg": price_avg,
        "price_min": price_min,
        "price_max": price_max,
        "sources_json": json.dumps(results),
        "difficulty": difficulty
    }

def get_market_study_for_material(material_id: int) -> dict | None:
    """
    Retrieves the latest market study data for a given material.
    """
    db = get_db()
    study = db.execute(
        '''SELECT mr.price_avg, mr.price_min, mr.price_max, mr.difficulty, mr.sources_json
           FROM market_research mr
           WHERE mr.material_id = ?
           ORDER BY mr.created_at DESC
           LIMIT 1''',
        (material_id,)
    ).fetchone()
    if study:
        return dict(study)
    return None

# --- Market Study Routes ---
@bp.route('/list')
@login_required
def list_market_studies():
    db = get_db()
    studies = db.execute(
        '''SELECT mr.id, m.nombre as material_name, mr.sector, mr.price_avg, mr.price_min, mr.price_max, mr.difficulty, mr.created_at
           FROM market_research mr
           JOIN materiales m ON mr.material_id = m.id
           ORDER BY mr.created_at DESC'''
    ).fetchall()
    return render_template('market_study/list.html', studies=studies)

@bp.route('/', methods=('GET', 'POST'))
@login_required
def market_study_form():
    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('index')) # Redirect to a safe page, e.g., index or login

    materials = db.execute('SELECT id, nombre FROM materiales ORDER BY nombre').fetchall()
    # services = get_service_choices() # Not directly used for material market study
    # freelancers = get_freelancer_choices() # Not directly used for material market study

    workload_advice = ""
    recommended_price = None

    if request.method == 'POST':
        error = None
        material_id = request.form.get('material_id', type=int)
        sector = request.form.get('sector')

        if not material_id or not sector:
            error = 'Material y Sector son obligatorios.'

        if error is not None:
            flash(error)
        else:
            try:
                # Fetch material name for web search simulation
                material_name_row = db.execute('SELECT nombre FROM materiales WHERE id = ?', (material_id,)).fetchone()
                material_name = material_name_row['nombre'] if material_name_row else 'Unknown Material'

                # Simulate web search
                search_results = mock_web_search(material_name, sector)

                db.execute(
                    '''INSERT INTO market_research (material_id, sector, price_avg, price_min, price_max, sources_json, difficulty)
                       VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (material_id, sector, search_results['price_avg'], search_results['price_min'],
                     search_results['price_max'], search_results['sources_json'], search_results['difficulty'])
                )
                db.commit()
                flash('¡Estudio de mercado añadido correctamente!')
                return redirect(url_for('market_study.list_market_studies'))
            except Exception as e:
                flash(f'Ocurrió un error inesperado: {e}', 'error')
                db.rollback()

    # Calculate workload advice and recommended price for rendering the form
    workload = get_current_workload()
    price_adjustment_factor = 1.0

    if workload > 15: # Example threshold for high workload
        workload_advice = "La agenda está muy llena. Se recomienda considerar un recargo del 20%."
        price_adjustment_factor = 1.2
    elif workload > 8: # Example threshold for medium workload
        workload_advice = "La agenda tiene una carga moderada. Podría aplicarse un pequeño recargo del 10%."
        price_adjustment_factor = 1.1
    else:
        workload_advice = "La agenda tiene una carga normal. No se recomienda ajuste por carga de trabajo."

    # If there's a material selected (e.g., on GET with pre-filled data or after an error), calculate recommended price
    if request.method == 'GET' and request.args.get('material_id'):
        material_id = request.args.get('material_id', type=int)
        material_name_row = db.execute('SELECT nombre FROM materiales WHERE id = ?', (material_id,)).fetchone()
        material_name = material_name_row['nombre'] if material_name_row else 'Unknown Material'
        sector = request.args.get('sector', 'General') # Default sector
        search_results = mock_web_search(material_name, sector)
        if search_results['price_avg'] is not None:
            recommended_price = search_results['price_avg'] * price_adjustment_factor

    return render_template('market_study/form.html', study=None, materials=materials, sectors=['Climatización', 'Obra', 'Electricidad', 'Fontanería', 'General'], workload_advice=workload_advice, recommended_price=recommended_price)

@bp.route('/<int:study_id>/edit', methods=('GET', 'POST'))
@login_required
def edit_market_study(study_id):
    db = get_db()
    study = db.execute('SELECT * FROM market_research WHERE id = ?', (study_id,)).fetchone()

    if study is None:
        flash('Estudio de mercado no encontrado.')
        return redirect(url_for('market_study.list_market_studies'))

    materials = get_material_choices() # Refactored

    workload_advice = ""
    recommended_price = None

    if request.method == 'POST':
        error = None
        material_id = request.form.get('material_id', type=int)
        sector = request.form.get('sector')

        if not material_id or not sector:
            error = 'Material y Sector son obligatorios.'

        if error is not None:
            flash(error)
        else:
            try:
                # Fetch material name for web search simulation
                material_name_row = db.execute('SELECT nombre FROM materiales WHERE id = ?', (material_id,)).fetchone()
                material_name = material_name_row['nombre'] if material_name_row else 'Unknown Material'

                # Simulate web search
                search_results = mock_web_search(material_name, sector)

                db.execute(
                    '''UPDATE market_research SET 
                       material_id = ?, sector = ?, price_avg = ?, price_min = ?, price_max = ?, sources_json = ?, difficulty = ?
                       WHERE id = ?''',
                    (material_id, sector, search_results['price_avg'], search_results['price_min'],
                     search_results['price_max'], search_results['sources_json'], search_results['difficulty'], study_id)
                )
                db.commit()
                flash('¡Estudio de mercado actualizado correctamente!')
                return redirect(url_for('market_study.list_market_studies'))
            except Exception as e:
                flash(f'Ocurrió un error inesperado: {e}', 'error')
                db.rollback()

    # Calculate workload advice and recommended price for rendering the form
    workload = get_current_workload()
    price_adjustment_factor = 1.0

    if workload > 15: # Example threshold for high workload
        workload_advice = "La agenda está muy llena. Se recomienda considerar un recargo del 20%."
        price_adjustment_factor = 1.2
    elif workload > 8: # Example threshold for medium workload
        workload_advice = "La agenda tiene una carga moderada. Podría aplicarse un pequeño recargo del 10%."
        price_adjustment_factor = 1.1
    else:
        workload_advice = "La agenda tiene una carga normal. No se recomienda ajuste por carga de trabajo."

    # If there's an existing study, calculate recommended price based on its material and sector
    if study:
        material_name_row = db.execute('SELECT nombre FROM materiales WHERE id = ?', (study['material_id'],)).fetchone()
        material_name = material_name_row['nombre'] if material_name_row else 'Unknown Material'
        sector = study['sector'] # Use existing study's sector
        search_results = mock_web_search(material_name, sector)
        if search_results['price_avg'] is not None:
            recommended_price = search_results['price_avg'] * price_adjustment_factor

    return render_template('market_study/form.html', study=study, materials=materials, sectors=['Climatización', 'Obra', 'Electricidad', 'Fontanería', 'General'], workload_advice=workload_advice, recommended_price=recommended_price)

@bp.route('/<int:study_id>/delete', methods=('POST',))
@login_required
def delete_market_study(study_id):
    db = get_db()
    db.execute('DELETE FROM market_research WHERE id = ?', (study_id,))
    db.commit()
    flash('¡Estudio de mercado eliminado correctamente!')
    return redirect(url_for('market_study.list_market_studies'))
