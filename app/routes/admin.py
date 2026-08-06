import math
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.auth import get_current_user
from app.database import get_db

router = APIRouter(prefix="/api/admin", tags=["admin"])

TABLE_PK_MAP = {
    "charts": "id",
    "analyses": "id",
    "notifications": "id",
    "settings": "key",
}


class BulkDeleteRequest(BaseModel):
    ids: Optional[List[Any]] = None
    keys: Optional[List[Any]] = None


def get_pk_field(table_name: str) -> str:
    if table_name not in TABLE_PK_MAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid or unsupported table: '{table_name}'. Supported tables: {list(TABLE_PK_MAP.keys())}",
        )
    return TABLE_PK_MAP[table_name]


FILTER_COLUMNS = {
    "enabled": ("enabled", lambda v: ("=", int(v))),
    "type": ("type", lambda v: ("=", v)),
    "direction": ("direction", lambda v: ("=", v.upper())),
    "min_score": ("score", lambda v: (">=", float(v))),
    "sent": ("sent", lambda v: ("=", int(v))),
    "status": ("status", lambda v: ("=", v)),
    "date_from": ("timestamp", lambda v: (">=", v)),
    "date_to": ("timestamp", lambda v: ("<=", v + "T23:59:59" if len(v) == 10 else v)),
}


@router.get("/{table}")
def list_admin_records(
    table: str,
    search: Optional[str] = None,
    enabled: Optional[str] = None,
    type: Optional[str] = None,
    direction: Optional[str] = None,
    min_score: Optional[float] = None,
    sent: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: Optional[str] = None,
    sort_dir: str = Query("desc", pattern="^(asc|desc|ASC|DESC)$"),
    user: str = Depends(get_current_user),
):
    pk = get_pk_field(table)
    db = get_db()

    # Get column names
    cols_cur = db.execute(f"PRAGMA table_info({table})")
    columns = [row["name"] for row in cols_cur.fetchall()]

    where_clauses = []
    params: List[Any] = []

    filter_values = {
        "enabled": enabled,
        "type": type,
        "direction": direction,
        "min_score": min_score,
        "sent": sent,
        "status": status,
        "date_from": date_from,
        "date_to": date_to,
    }
    for filter_key, value in filter_values.items():
        if value is None or value == "":
            continue
        column, build_op = FILTER_COLUMNS[filter_key]
        if column not in columns:
            continue
        try:
            op, param = build_op(value)
        except (TypeError, ValueError):
            continue
        where_clauses.append(f"{column} {op} ?")
        params.append(param)

    if search:
        search_like = f"%{search}%"
        sub_clauses = []
        for col in columns:
            sub_clauses.append(f"CAST({col} AS TEXT) LIKE ?")
            params.append(search_like)
        if sub_clauses:
            where_clauses.append("(" + " OR ".join(sub_clauses) + ")")

    where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    # Count total
    count_cur = db.execute(f"SELECT COUNT(*) as total FROM {table}{where_sql}", params)
    total = count_cur.fetchone()["total"]

    # Order clause
    order_col = sort_by if sort_by in columns else pk
    order_direction = sort_dir.upper()
    order_sql = f" ORDER BY {order_col} {order_direction}"

    # Pagination
    offset = (page - 1) * page_size
    query_sql = f"SELECT * FROM {table}{where_sql}{order_sql} LIMIT ? OFFSET ?"
    query_params = params + [page_size, offset]

    cur = db.execute(query_sql, query_params)
    rows = [dict(row) for row in cur.fetchall()]

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return {
        "items": rows,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "columns": columns,
        "pk": pk,
    }


@router.get("/{table}/{pk_val}")
def get_admin_record(
    table: str,
    pk_val: str,
    user: str = Depends(get_current_user),
):
    pk = get_pk_field(table)
    db = get_db()

    cur = db.execute(f"SELECT * FROM {table} WHERE {pk} = ?", (pk_val,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record not found in {table} with {pk}={pk_val}",
        )
    return dict(row)


@router.post("/{table}", status_code=status.HTTP_201_CREATED)
def create_admin_record(
    table: str,
    data: Dict[str, Any],
    user: str = Depends(get_current_user),
):
    pk = get_pk_field(table)
    db = get_db()

    cols_cur = db.execute(f"PRAGMA table_info({table})")
    valid_cols = {row["name"] for row in cols_cur.fetchall()}

    # Filter out invalid columns or auto-increment pk if not provided
    insert_data = {}
    for k, v in data.items():
        if k in valid_cols and (k != pk or (pk == "key" and k == "key")):
            if v == "" and k in ("id", "enabled", "score", "analysis_id", "created_at", "updated_at"):
                continue
            insert_data[k] = v

    if not insert_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid fields provided for insertion",
        )

    cols = list(insert_data.keys())
    placeholders = ", ".join(["?"] * len(cols))
    cols_sql = ", ".join(cols)
    values = list(insert_data.values())

    try:
        cur = db.execute(
            f"INSERT INTO {table} ({cols_sql}) VALUES ({placeholders})", values
        )
        db.commit()
        new_pk = cur.lastrowid if pk == "id" else insert_data.get("key")
        
        row_cur = db.execute(f"SELECT * FROM {table} WHERE {pk} = ?", (new_pk,))
        return dict(row_cur.fetchone())
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create record: {str(e)}",
        )


@router.put("/{table}/{pk_val}")
def update_admin_record(
    table: str,
    pk_val: str,
    data: Dict[str, Any],
    user: str = Depends(get_current_user),
):
    pk = get_pk_field(table)
    db = get_db()

    cols_cur = db.execute(f"PRAGMA table_info({table})")
    valid_cols = {row["name"] for row in cols_cur.fetchall()}

    update_data = {}
    for k, v in data.items():
        if k in valid_cols and k != pk:
            if v == "" and k in ("id", "enabled", "score", "analysis_id", "created_at", "updated_at"):
                continue
            update_data[k] = v

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update",
        )

    set_clauses = [f"{col} = ?" for col in update_data.keys()]
    set_sql = ", ".join(set_clauses)
    values = list(update_data.values()) + [pk_val]

    try:
        cur = db.execute(f"UPDATE {table} SET {set_sql} WHERE {pk} = ?", values)
        db.commit()
        if cur.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Record with {pk}={pk_val} not found",
            )
        row_cur = db.execute(f"SELECT * FROM {table} WHERE {pk} = ?", (pk_val,))
        return dict(row_cur.fetchone())
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update record: {str(e)}",
        )


@router.delete("/{table}/{pk_val}")
def delete_admin_record(
    table: str,
    pk_val: str,
    user: str = Depends(get_current_user),
):
    pk = get_pk_field(table)
    db = get_db()

    cur = db.execute(f"DELETE FROM {table} WHERE {pk} = ?", (pk_val,))
    db.commit()
    if cur.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record with {pk}={pk_val} not found",
        )
    return {"status": "deleted", "id": pk_val, "table": table}


@router.post("/{table}/bulk-delete")
def bulk_delete_admin_records(
    table: str,
    body: BulkDeleteRequest,
    user: str = Depends(get_current_user),
):
    pk = get_pk_field(table)
    db = get_db()

    items_to_delete = body.ids if body.ids is not None else body.keys
    if not items_to_delete:
        return {"deleted_count": 0}

    placeholders = ", ".join(["?"] * len(items_to_delete))
    cur = db.execute(
        f"DELETE FROM {table} WHERE {pk} IN ({placeholders})", items_to_delete
    )
    db.commit()
    return {"deleted_count": cur.rowcount, "table": table}
