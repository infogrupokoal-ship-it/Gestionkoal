
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch

def generate_quote_pdf(file_path, quote_data, items_data, client_data, company_data):
    c = canvas.Canvas(file_path, pagesize=letter)
    width, height = letter

    # Company Info
    c.setFont('Helvetica-Bold', 16)
    c.drawString(inch, height - inch, company_data['name'])
    c.setFont('Helvetica', 10)
    c.drawString(inch, height - inch - 0.25*inch, company_data['address'])
    c.drawString(inch, height - inch - 0.4*inch, f"CIF: {company_data['cif']}")

    # Quote Info
    c.setFont('Helvetica-Bold', 12)
    c.drawString(inch, height - 2*inch, f"Presupuesto #{quote_data['id']}")
    c.setFont('Helvetica', 10)
    c.drawString(inch, height - 2*inch - 0.25*inch, f"Fecha: {quote_data['fecha_creacion']}")
    if quote_data.get('fecha_vencimiento'):
        c.drawString(inch, height - 2*inch - 0.4*inch, f"Válido hasta: {quote_data['fecha_vencimiento']}")

    # Client Info
    c.setFont('Helvetica-Bold', 12)
    c.drawString(width - 3*inch, height - 2*inch, "Cliente:")
    c.setFont('Helvetica', 10)
    c.drawString(width - 3*inch, height - 2*inch - 0.25*inch, client_data['nombre'])
    if client_data.get('nif'):
        c.drawString(width - 3*inch, height - 2*inch - 0.4*inch, f"NIF: {client_data['nif']}")
    if client_data.get('direccion'):
        c.drawString(width - 3*inch, height - 2*inch - 0.55*inch, client_data['direccion'])

    # Items Table
    c.setFont('Helvetica-Bold', 10)
    y_position = height - 3.5*inch
    c.drawString(inch, y_position, "Descripción")
    c.drawString(inch + 4*inch, y_position, "Cantidad")
    c.drawString(inch + 5*inch, y_position, "Precio Unit.")
    c.drawString(inch + 6*inch, y_position, "Total")
    c.line(inch, y_position - 0.1*inch, width - inch, y_position - 0.1*inch)

    c.setFont('Helvetica', 10)
    y_position -= 0.3*inch

    for item in items_data:
        c.drawString(inch, y_position, item['descripcion'])
        c.drawString(inch + 4*inch, y_position, str(item['qty']))
        c.drawString(inch + 5*inch, y_position, f"{item['precio_unit']:.2f} €")
        c.drawString(inch + 6*inch, y_position, f"{item['qty'] * item['precio_unit']:.2f} €")
        y_position -= 0.25*inch

    # Total
    c.line(inch, y_position, width - inch, y_position)
    y_position -= 0.3*inch
    c.setFont('Helvetica-Bold', 12)
    c.drawString(inch + 5*inch, y_position, "Total:")
    c.drawString(inch + 6*inch, y_position, f"{quote_data['total']:.2f} €")

    # Signature
    if quote_data.get('client_signed_by'):
        y_position -= 1*inch
        c.setFont('Helvetica', 10)
        c.drawString(inch, y_position, f"Firmado por: {quote_data['client_signed_by']}")
        c.drawString(inch, y_position - 0.2*inch, f"Fecha de firma: {quote_data['client_signature_date']}")

    c.save()
