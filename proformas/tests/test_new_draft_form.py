import pytest
from django.urls import reverse

from proformas.forms import NewDraftForm
from proformas.models import Client, Site

pytestmark = [pytest.mark.django_db]


@pytest.mark.unit
def test_new_draft_form_rejects_site_from_other_client(site):
    other = Client.objects.create(
        kind=Client.Kind.COMPANY,
        name="Other Co",
        phone="910000001",
        email="other@example.com",
    )
    other_site = Site.objects.create(
        client=other,
        alias_1="Other site",
        street="Rua 1",
        postal_code="1000-001",
        city="Lisboa",
        phone="910000002",
        email="other-site@example.com",
    )
    form = NewDraftForm(
        data={"client": str(site.client.pk), "site": str(other_site.pk)}
    )
    assert not form.is_valid()
    assert "site" in form.errors


@pytest.mark.unit
def test_new_draft_site_queryset_puts_hq_first(site):
    hq = Site.objects.create(
        client=site.client,
        is_headquarters=True,
        alias_1="Zebra HQ",
        street="Rua HQ 1",
        postal_code="1000-010",
        city="Lisboa",
        phone="910000010",
        email="hq@example.com",
    )
    form = NewDraftForm()
    sites = list(form.fields["site"].queryset.filter(client=site.client))
    assert sites[0].pk == hq.pk


@pytest.mark.integration
def test_create_draft_via_drawer(client, staff_user, site):
    client.force_login(staff_user)
    response = client.post(
        reverse("proforma_list"),
        {
            "action": "create",
            "client": str(site.client.pk),
            "site": str(site.pk),
        },
    )
    assert response.status_code == 302
    assert Site.objects.get(pk=site.pk).proformas.filter(status="draft").exists()
