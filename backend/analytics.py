"""Analytics endpoints for the PennyWise backend API."""

import numpy as np
import pandas as pd
from flask import Blueprint, jsonify

from backend.db import get_collection

analytics_bp = Blueprint("analytics", __name__)


def _fetch_transactions_df():
    """Fetch all transactions from MongoDB and return as a DataFrame."""
    collection = get_collection()
    records = list(collection.find())
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    return df


@analytics_bp.route("/monthly-summary", methods=["GET"])
def monthly_summary():
    """Return total income and expenses grouped by month."""
    df = _fetch_transactions_df()
    if df.empty:
        return jsonify({"monthly_summary": []}), 200

    df["month"] = df["date"].dt.to_period("M").astype(str)

    summary = (
        df.groupby(["month", "type"])["amount"]
        .sum()
        .unstack(fill_value=0)
        .reset_index()
    )

    result = []
    for _, row in summary.iterrows():
        result.append(
            {
                "month": row["month"],
                "income": float(row.get("income", 0)),
                "expense": float(row.get("expense", 0)),
                "net": float(row.get("income", 0) - row.get("expense", 0)),
            }
        )

    return jsonify({"monthly_summary": result}), 200


@analytics_bp.route("/spending-trends", methods=["GET"])
def spending_trends():
    """Return month-over-month spending trend percentages."""
    df = _fetch_transactions_df()
    if df.empty:
        return jsonify({"spending_trends": []}), 200

    expenses = df[df["type"] == "expense"].copy()
    if expenses.empty:
        return jsonify({"spending_trends": []}), 200

    expenses["month"] = expenses["date"].dt.to_period("M").astype(str)
    monthly = expenses.groupby("month")["amount"].sum().sort_index()

    pct_changes = monthly.pct_change().replace({np.nan: None}).tolist()
    months = monthly.index.tolist()
    amounts = monthly.values.tolist()

    result = []
    for i, month in enumerate(months):
        entry = {"month": month, "total_spent": float(amounts[i])}
        if pct_changes[i] is not None:
            entry["change_pct"] = round(float(pct_changes[i]) * 100, 2)
        else:
            entry["change_pct"] = None
        result.append(entry)

    return jsonify({"spending_trends": result}), 200


@analytics_bp.route("/top-categories", methods=["GET"])
def top_categories():
    """Return top spending categories ranked by total amount."""
    df = _fetch_transactions_df()
    if df.empty:
        return jsonify({"top_categories": []}), 200

    expenses = df[df["type"] == "expense"].copy()
    if expenses.empty:
        return jsonify({"top_categories": []}), 200

    grouped = (
        expenses.groupby("category")["amount"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )

    total = grouped["amount"].sum()
    result = []
    for _, row in grouped.iterrows():
        result.append(
            {
                "category": row["category"],
                "total_spent": float(row["amount"]),
                "percentage": round(float(row["amount"] / total * 100), 2)
                if total > 0
                else 0.0,
            }
        )

    return jsonify({"top_categories": result}), 200
