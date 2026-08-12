from sqlalchemy import create_engine, inspect

from app.db.base import Base
import app.models  # noqa: F401


def test_expected_tables_and_offer_headers_column_exist():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    inspector = inspect(engine)

    assert set(inspector.get_table_names()) == {
        "companies",
        "offers",
        "monthly_vehicle_incentives",
        "scrape_runs",
    }

    offer_columns = {column["name"] for column in inspector.get_columns("offers")}
    assert "excel_headers" in offer_columns
    assert "file_url" in offer_columns

    incentive_columns = {
        column["name"]
        for column in inspector.get_columns("monthly_vehicle_incentives")
    }
    assert "offer_priority" in incentive_columns
    assert "impel_model_movers" in incentive_columns
