from scripts.seed import count_cases, slugify, title_from_slug


def test_title_from_slug():
    assert title_from_slug("best-time-to-buy-and-sell-stock-ii") == "Best Time to Buy and Sell Stock II"
    assert title_from_slug("a-number-after-a-double-reversal") == "A Number After a Double Reversal"


def test_slugify():
    assert slugify("Heap (Priority Queue)") == "heap-priority-queue"
    assert slugify("AQR Capital Management") == "aqr-capital-management"


def test_count_cases(sample):
    assert count_cases(sample["two-sum"]["test"]) == 12


def test_reseed_keeps_ids(client):
    from app.db import SessionLocal
    from app.models import Problem
    from scripts.seed import seed
    from tests.conftest import COMPANIES, SAMPLE

    with SessionLocal() as db:
        before = {p.slug: p.id for p in db.query(Problem)}
        stats = seed(db, SAMPLE, COMPANIES)
        after = {p.slug: p.id for p in db.query(Problem)}
    assert before == after
    assert stats["problems_with_company_tags"] == 3
