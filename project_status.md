## Project Environment and Deployment:

### Server Information:
- **Deployment Platform:** Render.com
- **Known Deployment Issues:** Persistent 404 errors on root path, discrepancies between local and deployed `app.py` content (suggesting caching or deployment issues on Render's side). Database connection issues (`AttributeError: 'NoneType' object has no attribute 'fetchall'`) indicating problems with Render's PostgreSQL setup or connection string handling.

### Project Access Link:
- **Render Deployment URL:** [Insert actual Render deployment URL here, if available and user provides it]

### Tools and Technologies:
- **Backend:** Flask (Python)
- **Database:** PostgreSQL (on Render), SQLite (local development fallback)
- **Frontend:** HTML, CSS, JavaScript (Jinja2 templating)
- **Version Control:** Git
- **Package Manager:** pip

## Example Data Used in `init-db` (Prefixed with "ejem."):

### Client Example:
- **Name:** ejem. Maria Dolores
- **Address:** Calle Maldiva, 24
- **Phone:** 666555444
- **Email:** ejemplo@email.com

### Provider Example:
- **Name:** ejem. Ferreteria La Esquina
- **Contact Person:** Juan Perez
- **Phone:** 960000000
- **Email:** info@ferreteria.com
- **Address:** Calle de la Ferreteria 1, Valencia
- **Type:** Ferreteria

### Material Example:
- **Name:** ejem. Martillo (Hammer)
- **Description:** Martillo de carpintero (Carpenter's hammer)
- **Current Stock:** 10
- **Unit Price:** 15.00
- **Recommended Price:** 18.00
- **Last Sold Price:** 14.00

### Service Example:
- **Name:** ejem. Fontaneria (Plumbing)
- **Description:** Instalacion de grifo (Faucet installation)
- **Price:** 50.00
- **Recommended Price:** 55.00
- **Last Sold Price:** 48.00

### Job Example:
- **Title:** ejem. Reparacion de persiana (ejem. Shutter repair)
- **Description:** La persiana del dormitorio no baja (The bedroom shutter does not go down)
- **Status:** Pendiente
- **Budget:** 100.00
- **VAT Rate:** 21.0
- **Difficulty Rating:** 2

### Task Example:
- **Title:** ejem. Comprar lamas (Buy slats)
- **Description:** Comprar lamas de persiana (Buy shutter slats)
- **Status:** Pendiente
- **Payment Method:** Efectivo
- **Payment Status:** Pendiente
- **Amount Paid:** 0.00

---