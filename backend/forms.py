from flask_wtf import FlaskForm
from wtforms import BooleanField, FloatField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, NumberRange, Optional, Length


class MaterialForm(FlaskForm):
    sku = StringField("SKU")
    nombre = StringField("Nombre", validators=[DataRequired()])
    categoria = StringField("Categoría")
    unidad_medida = StringField("Unidad de Medida")
    stock_actual = FloatField("Stock Actual", default=0, validators=[NumberRange(min=0)])
    stock_minimo = FloatField("Stock Mínimo", default=0, validators=[NumberRange(min=0)])
    ubicacion = StringField("Ubicación")
    precio_costo_estimado = FloatField(
        "Precio Costo Estimado", default=0.0, validators=[NumberRange(min=0)]
    )
    precio_venta_sugerido = FloatField("Precio Venta Sugerido", validators=[Optional(), NumberRange(min=0)])
    proveedor_sugerido = StringField("Proveedor Sugerido")
    tiempo_entrega_dias = FloatField("Tiempo de Entrega (días)", validators=[Optional(), NumberRange(min=0)])
    observaciones = StringField("Observaciones", validators=[Optional(), Length(max=500)])
    fecha_ultimo_ingreso = StringField("Fecha Último Ingreso (YYYY-MM-DD)", validators=[Optional()])
    cantidad_total_usada = FloatField("Cantidad Total Usada", default=0, validators=[NumberRange(min=0)])
    proveedor_id = SelectField("Proveedor Principal", coerce=int, validators=[Optional()])
    comision_empresa = FloatField(
        "Comisión de Empresa (%)", default=0.0, validators=[NumberRange(min=0, max=100)]
    )
    submit = SubmitField("Guardar Material")


class ClientForm(FlaskForm):
    nombre = StringField("Nombre", validators=[DataRequired()])
    telefono = StringField("Teléfono")
    email = StringField("Email", validators=[Optional(), Email()])
    nif = StringField("NIF")
    is_ngo = BooleanField("Es ONG")
    submit = SubmitField("Guardar Cliente")


class ProviderForm(FlaskForm):
    nombre = StringField("Nombre", validators=[DataRequired()])
    contacto = StringField("Persona de Contacto")
    telefono = StringField("Teléfono")
    email = StringField("Email", validators=[Optional(), Email()])
    direccion = StringField("Dirección")
    nif = StringField("NIF")
    tipo = SelectField("Tipo de Proveedor", choices=[('material', 'Material'), ('servicio', 'Servicio'), ('mixto', 'Mixto')], validators=[DataRequired()])
    is_active = BooleanField("Activo", default=True)
    whatsapp_number = StringField("Número de WhatsApp")
    whatsapp_opt_in = BooleanField("Opt-in WhatsApp")
    submit = SubmitField("Guardar Proveedor")
