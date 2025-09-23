from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from datetime import datetime
import os

def generate_receipt_pdf(output_path, job_details, client_details, company_details, technician_details=None):
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Company Details
    story.append(Paragraph(company_details.get('name', 'Grupo Koal'), styles['h1']))
    story.append(Paragraph(company_details.get('address', 'Dirección de la Empresa'), styles['Normal']))
    story.append(Paragraph(company_details.get('phone', 'Teléfono de la Empresa'), styles['Normal']))
    story.append(Paragraph(company_details.get('email', 'Email de la Empresa'), styles['Normal']))
    story.append(Spacer(1, 0.2 * inch))

    # Receipt Title and Date
    story.append(Paragraph(f"Recibo de Pago - Trabajo #{job_details['id']}", styles['h2']))
    story.append(Paragraph(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    story.append(Spacer(1, 0.2 * inch))

    # Client Details
    story.append(Paragraph("Detalles del Cliente:", styles['h3']))
    story.append(Paragraph(f"Nombre: {client_details.get('name', 'N/A')}", styles['Normal']))
    story.append(Paragraph(f"Teléfono: {client_details.get('phone', 'N/A')}", styles['Normal']))
    story.append(Paragraph(f"Email: {client_details.get('email', 'N/A')}", styles['Normal']))
    story.append(Spacer(1, 0.2 * inch))

    # Job Details
    story.append(Paragraph("Detalles del Trabajo:", styles['h3']))
    story.append(Paragraph(f"Descripción: {job_details.get('description', 'N/A')}", styles['Normal']))
    story.append(Paragraph(f"Estado: {job_details.get('status', 'N/A')}", styles['Normal']))
    story.append(Paragraph(f"Método de Pago: {job_details.get('payment_method', 'N/A')}", styles['Normal']))
    story.append(Paragraph(f"Estado de Pago: {job_details.get('payment_status', 'N/A')}", styles['Normal']))
    story.append(Spacer(1, 0.2 * inch))

    # Technician Details (if provided)
    if technician_details:
        story.append(Paragraph("Detalles del Técnico:", styles['h3']))
        story.append(Paragraph(f"Nombre: {technician_details.get('name', 'N/A')}", styles['Normal']))
        story.append(Paragraph(f"Teléfono: {technician_details.get('phone', 'N/A')}", styles['Normal']))
        story.append(Spacer(1, 0.2 * inch))

    # Amount Paid
    story.append(Paragraph(f"Monto Pagado: {job_details.get('amount', 0.0):.2f} €", styles['h2']))
    story.append(Spacer(1, 0.5 * inch))

    # Signature Line (Placeholder for digital signature or client confirmation)
    story.append(Paragraph("__________________________________", styles['Normal']))
    story.append(Paragraph("Firma del Cliente / Confirmación de Pago", styles['Normal']))

    doc.build(story)
