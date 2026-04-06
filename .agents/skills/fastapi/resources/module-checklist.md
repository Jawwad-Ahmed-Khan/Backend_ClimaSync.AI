# New Module Creation Checklist

Step-by-step guide for creating a new feature module under `app/modules/<module_name>/`.

## Prerequisites

- [ ] Module purpose and scope defined
- [ ] Database schema/ERD designed
- [ ] API endpoints identified (routes, methods, auth requirements)

## 1. Create Module Files

```
app/modules/<module_name>/
├── __init__.py
├── router.py
├── schemas.py
├── models.py
├── service.py
├── repository.py
├── dependencies.py
├── exceptions.py
└── constants.py
```

- [ ] Create directory `app/modules/<module_name>/`
- [ ] Create `__init__.py` with router export
- [ ] Create `constants.py` for module-specific enums and constants

## 2. Define ORM Models (`models.py`)

- [ ] Create model class extending `BaseModel` (UUID PK + timestamps)
- [ ] Add `SoftDeleteMixin` if soft-delete is needed
- [ ] Define all columns with `Mapped[]` type annotations
- [ ] Add `__tablename__` (plural, snake_case)
- [ ] Add relationships with `lazy` strategy specified
- [ ] Add database indexes for query-heavy columns
- [ ] Add `__repr__` for debugging

> **Reference**: `examples/model.py`

## 3. Define Schemas (`schemas.py`)

- [ ] `<Model>Base` — shared fields (for inheritance)
- [ ] `<Model>Create` — request body (strict: all required fields)
- [ ] `<Model>Update` — partial update (all fields optional, `@model_validator` for non-empty)
- [ ] `<Model>Read` — response model (`ConfigDict(from_attributes=True)`, includes `id` + timestamps)
- [ ] `<Model>List` — extends `PaginatedResponse[<Model>Read]`
- [ ] Add field validators (`@field_validator`) for business rules
- [ ] Set `Field(...)` with `min_length`, `max_length`, `examples`, `description`
- [ ] Verify passwords/secrets are **never** in Read schemas

> **Reference**: `examples/schema.py`

## 4. Implement Repository (`repository.py`)

- [ ] Extend `BaseRepository[<Model>]`
- [ ] Constructor: `super().__init__(<Model>, session)`
- [ ] Add domain-specific queries (e.g., `get_by_email`, `get_active`)
- [ ] Use parameterized queries (never f-strings in SQL)
- [ ] Use `selectinload` / `joinedload` for relationships

> **Reference**: `examples/repository.py`

## 5. Implement Service (`service.py`)

- [ ] Constructor accepts repository (injected via DI)
- [ ] Implement CRUD methods: `get_by_id`, `list`, `create`, `update`, `delete`
- [ ] Enforce business rules (uniqueness checks, authorization)
- [ ] Raise `AppException` subclasses (NOT `HTTPException`)
- [ ] Transform between schemas and models (`model_validate`)
- [ ] Add logging for create/update/delete operations

> **Reference**: `examples/service.py`

## 6. Wire Dependencies (`dependencies.py`)

- [ ] `get_<module>_repository(db: DbSession) -> <Module>Repository`
- [ ] `get_<module>_service(repo: Depends(get_repo)) -> <Module>Service`
- [ ] Add any module-specific dependencies

> **Reference**: `examples/dependencies.py`

## 7. Define Routes (`router.py`)

- [ ] Create `router = APIRouter()`
- [ ] Define type aliases: `Service = Annotated[..., Depends(...)]`
- [ ] Implement endpoints:
  - [ ] `GET /` — list (paginated, requires auth)
  - [ ] `GET /{id}` — get by ID
  - [ ] `POST /` — create (status 201)
  - [ ] `PATCH /{id}` — partial update
  - [ ] `DELETE /{id}` — delete (status 204)
- [ ] Set `response_model`, `status_code`, `summary` on every endpoint
- [ ] Use `Depends(get_current_user)` or `Depends(require_role(...))` for auth

> **Reference**: `examples/router.py`

## 8. Register Router

- [ ] Open `app/main.py` → `_register_routers()`
- [ ] Add: `app.include_router(<module>_router, prefix=f"{api_prefix}/<module>", tags=["<Module>"])`

## 9. Create & Apply Migration

```bash
alembic revision --autogenerate -m "add_<module_name>_table"
```

- [ ] Review generated migration file
- [ ] Verify `upgrade()` and `downgrade()` are both correct
- [ ] Apply: `alembic upgrade head`

## 10. Write Tests

### Unit Tests (`tests/unit/modules/<module_name>/`)

- [ ] `test_service.py` — mock repository, test business logic
- [ ] `test_schemas.py` — test validators and edge cases

### Integration Tests (`tests/integration/modules/<module_name>/`)

- [ ] `test_router.py` — test endpoints via AsyncClient
- [ ] Test happy paths AND error paths (404, 409, 422, 401, 403)

> **Reference**: `examples/testing.py`

## 11. Final Verification

- [ ] `ruff check app/modules/<module_name>/` — no lint errors
- [ ] `mypy app/modules/<module_name>/` — no type errors
- [ ] `pytest tests/ -v` — all tests pass
- [ ] `pytest --cov=app/modules/<module_name>/` — coverage ≥ 80%
- [ ] API docs at `/docs` show new endpoints correctly
