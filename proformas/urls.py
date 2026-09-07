from django.urls import path

from . import views

urlpatterns = [
    path("clients/", views.client_list, name="client_list"),
    path("sites/", views.site_list, name="site_list"),
    path("proformas/", views.proforma_list, name="proforma_list"),
    path("proformas/change/", views.proforma_change, name="proforma_change"),
    path("proformas/outcome/", views.proforma_outcome, name="proforma_outcome"),
    path("proformas/<int:pk>/", views.proforma_detail, name="proforma_detail"),
    path("proformas/<int:pk>/quote/", views.proforma_quote, name="proforma_quote"),
    path("proformas/<int:pk>/pdf/", views.proforma_pdf, name="proforma_pdf"),
    path("items/", views.item_list, name="item_list"),
    path("families/", views.family_list, name="family_list"),
    path("sub-families/", views.sub_family_list, name="sub_family_list"),
    path("manufacturers/", views.manufacturer_list, name="manufacturer_list"),
    path(
        "manufacturers/<int:pk>/",
        views.manufacturer_pricelist,
        name="manufacturer_pricelist",
    ),
    path("powers/", views.power_list, name="power_list"),
    path("vat-rates/", views.vat_rate_list, name="vat_rate_list"),
    path("parameters/", views.parameter_list, name="parameter_list"),
    path("tubing-lengths/", views.tubing_length_list, name="tubing_length_list"),
    path("positions/", views.contact_position_list, name="contact_position_list"),
]
