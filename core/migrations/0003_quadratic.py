from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_linear_equations'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='exercise',
            name='exercise_valid_parameters',
        ),
        migrations.AlterField(
            model_name='exercise',
            name='kind',
            field=models.CharField(
                choices=[
                    ('common', 'Fator comum'),
                    ('squares', 'Diferença de quadrados'),
                    ('linear', 'Equação do primeiro grau'),
                    ('quadratic', 'Equação do segundo grau'),
                ],
                max_length=9,
            ),
        ),
        migrations.AddConstraint(
            model_name='exercise',
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(
                        models.Q(kind__in=['common', 'squares'], a__gte=1, b__gte=1, c__isnull=True),
                        models.Q(
                            models.Q(kind='linear', a__gte=-5, a__lte=5,
                                     b__gte=-10, b__lte=10, c__isnull=False,
                                     c__gte=-55, c__lte=55),
                            models.Q(a=0, _negated=True),
                        ),
                        models.Q(
                            models.Q(kind='quadratic', a__gte=-3, a__lte=3,
                                     b__gte=-36, b__lte=36, c__isnull=False,
                                     c__gte=-108, c__lte=108),
                            models.Q(a=0, _negated=True),
                        ),
                        _connector='OR',
                    )
                ),
                name='exercise_valid_parameters',
            ),
        ),
    ]
