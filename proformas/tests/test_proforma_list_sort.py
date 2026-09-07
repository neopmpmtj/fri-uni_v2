import pytest
from django.urls import reverse

from proformas.models import Proforma
from proformas.services import add_line, create_draft, issue_proforma

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def test_proforma_list_default_sort_number_desc(client, staff_user, site, indoor):
    older = create_draft(site, staff_user)
    add_line(older, indoor, staff_user)
    issue_proforma(older, staff_user)
    newer = create_draft(site, staff_user)
    add_line(newer, indoor, staff_user)
    issue_proforma(newer, staff_user)
    client.force_login(staff_user)

    response = client.get(reverse("proforma_list"))
    assert response.status_code == 200
    assert response.context["sort"] == "number"
    assert response.context["dir"] == "desc"
    numbers = [row.number for row in response.context["proformas"]]
    assert numbers.index(newer.number) < numbers.index(older.number)


def test_proforma_list_sort_by_updated_asc(client, staff_user, site, indoor):
    first = create_draft(site, staff_user)
    add_line(first, indoor, staff_user)
    issue_proforma(first, staff_user)
    second = create_draft(site, staff_user)
    add_line(second, indoor, staff_user)
    issue_proforma(second, staff_user)
    client.force_login(staff_user)

    response = client.get(
        reverse("proforma_list"),
        {"sort": "updated", "dir": "asc"},
    )
    assert response.status_code == 200
    numbers = [row.number for row in response.context["proformas"]]
    assert numbers.index(first.number) < numbers.index(second.number)


def test_proforma_list_sort_links_preserve_filters(client, staff_user):
    client.force_login(staff_user)
    response = client.get(
        reverse("proforma_list"),
        {"q": "PF", "status": "issued", "sort": "number", "dir": "desc"},
    )
    assert response.status_code == 200
    url = response.context["sort_urls"]["site"]
    assert "q=PF" in url
    assert "status=issued" in url
