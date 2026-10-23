import time

import fitz


def test_twenty_five_page_pdf_inspection_and_render_stays_responsive(client, tmp_path):
    source = tmp_path / "performans.pdf"
    document = fitz.open()
    for index in range(25):
        page = document.new_page(width=595, height=842)
        page.insert_text((72, 96), f"Performans sayfasi {index + 1}", fontsize=12)
    document.save(source)
    document.close()

    started = time.perf_counter()
    with source.open("rb") as handle:
        uploaded = client.post("/api/files", files={"file": (source.name, handle, "application/pdf")})
    assert uploaded.status_code == 200, uploaded.text
    document_id = uploaded.json()["data"]["id"]
    assert uploaded.json()["data"]["pdf"]["page_count"] == 25
    rendered = client.get(f"/api/pdf/{document_id}/pages/12/render", params={"scale": 1})
    elapsed = time.perf_counter() - started

    assert rendered.status_code == 200, rendered.text
    assert rendered.content.startswith(b"\x89PNG")
    # CI ve düşük güçlü Windows makinelerinde de kararlı kalacak gevşek üst sınır.
    assert elapsed < 15
