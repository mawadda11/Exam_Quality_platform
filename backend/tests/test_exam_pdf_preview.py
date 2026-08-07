from __future__ import annotations

import io
from io import BytesIO

from fastapi.testclient import TestClient
from helpers import auth_header, valid_pdf_bytes
from PIL import Image

PAYLOAD = {
    "course": {"code": "PREVIEW-101", "name": "Visual Review"},
    "exam_type": "Final",
    "term": "2026",
}


def _create_with_exam(client: TestClient, email: str) -> str:
    created = client.post("/api/v1/analyses", json=PAYLOAD, headers=auth_header(email))
    assert created.status_code == 201
    analysis_id = str(created.json()["id"])
    uploaded = client.post(
        f"/api/v1/analyses/{analysis_id}/files",
        headers=auth_header(email),
        data={"file_type": "exam"},
        files={"file": ("exam.pdf", io.BytesIO(valid_pdf_bytes()), "application/pdf")},
    )
    assert uploaded.status_code == 201
    return analysis_id


def test_owner_can_render_authenticated_exam_page_and_crop(client: TestClient) -> None:
    email = "visual-preview-owner@example.edu"
    analysis_id = _create_with_exam(client, email)
    headers = auth_header(email)

    page = client.get(
        f"/api/v1/analyses/{analysis_id}/files/exam/pages/1/image",
        headers=headers,
    )
    assert page.status_code == 200, page.text
    assert page.headers["content-type"].startswith("image/png")
    assert page.headers["cache-control"] == "private, no-store"
    assert page.content.startswith(b"\x89PNG\r\n\x1a\n")
    page_image = Image.open(BytesIO(page.content))

    repeated_page = client.get(
        f"/api/v1/analyses/{analysis_id}/files/exam/pages/1/image",
        headers=headers,
    )
    assert repeated_page.status_code == 200, repeated_page.text
    assert repeated_page.content == page.content

    crop = client.get(
        f"/api/v1/analyses/{analysis_id}/files/exam/pages/1/image",
        headers=headers,
        params={
            "x0": 20,
            "top": 20,
            "x1": 300,
            "bottom": 120,
            "crop": "true",
            "padding": 4,
        },
    )
    assert crop.status_code == 200, crop.text
    crop_image = Image.open(BytesIO(crop.content))
    assert crop_image.width < page_image.width
    assert crop_image.height < page_image.height


def test_exam_page_preview_requires_complete_geometry_and_owner_access(
    client: TestClient,
) -> None:
    email = "visual-preview-private@example.edu"
    analysis_id = _create_with_exam(client, email)

    partial = client.get(
        f"/api/v1/analyses/{analysis_id}/files/exam/pages/1/image",
        headers=auth_header(email),
        params={"x0": 20},
    )
    assert partial.status_code == 422

    missing_page = client.get(
        f"/api/v1/analyses/{analysis_id}/files/exam/pages/99/image",
        headers=auth_header(email),
    )
    assert missing_page.status_code == 404

    intruder = client.get(
        f"/api/v1/analyses/{analysis_id}/files/exam/pages/1/image",
        headers=auth_header("visual-preview-intruder@example.edu"),
    )
    assert intruder.status_code == 404
