import pytest
from django.urls import reverse

from accounts.lang import normalize_lang
from accounts.models import User


@pytest.mark.integration
@pytest.mark.django_db
def test_anonymous_home_redirects_to_login(client):
    response = client.get("/")
    assert response.status_code == 302
    assert reverse("login") in response.url


@pytest.mark.integration
@pytest.mark.django_db
def test_staff_forbidden_on_admin(client):
    user = User.objects.create_user(
        email="staff@example.com", password="pass12345", role=User.Role.STAFF
    )
    client.force_login(user)
    response = client.get("/admin/")
    assert response.status_code == 403


@pytest.mark.unit
def test_normalize_lang_pt_pt():
    assert normalize_lang("pt-PT") == "pt"
    assert normalize_lang("en") == "en"


@pytest.mark.integration
@pytest.mark.django_db
def test_dashboard_has_language_select(client):
    user = User.objects.create_user(email="a@example.com", password="pass12345")
    client.force_login(user)
    response = client.get("/")
    assert response.status_code == 200
    content = response.content.decode()
    assert 'id="pref-language"' in content


@pytest.mark.integration
@pytest.mark.django_db
def test_work_page_has_no_language_select(client):
    user = User.objects.create_user(email="a@example.com", password="pass12345")
    client.force_login(user)
    response = client.get("/clients/")
    assert response.status_code == 200
    content = response.content.decode()
    assert 'id="pref-language"' not in content
    assert "topbar" in content
