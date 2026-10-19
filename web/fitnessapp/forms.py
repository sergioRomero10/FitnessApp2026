"""Formularios con validación en el servidor (Flask-WTF también añade la protección CSRF).

Antes se hacía int(request.form['quantity']) directamente: un texto vacío o negativo
provocaba un error 500.
"""

from flask_wtf import FlaskForm
from wtforms import DateField, HiddenField, IntegerField, SelectField, StringField
from wtforms.validators import DataRequired, Length, NumberRange, ValidationError


class DietForm(FlaskForm):
    name = StringField("Diet name", validators=[DataRequired(), Length(max=60)])
    start_date = DateField("Start date", validators=[DataRequired()])
    end_date = DateField("End date", validators=[DataRequired()])

    def validate_end_date(self, field):
        if self.start_date.data and field.data and field.data < self.start_date.data:
            raise ValidationError("The end date cannot be before the start date.")


class AddItemForm(FlaskForm):
    food = SelectField("Food", validators=[DataRequired()], choices=[])
    grams = IntegerField(
        "Amount (g/ml)", validators=[DataRequired(), NumberRange(min=1, max=5000)], default=100
    )


class FoodKeyForm(FlaskForm):
    """Formulario de un solo campo oculto (favorito, quitar de la dieta...)."""

    key = HiddenField(validators=[DataRequired(), Length(max=200)])


class EmptyForm(FlaskForm):
    """Solo aporta el token CSRF (borrar dieta, cerrar sesión...)."""
