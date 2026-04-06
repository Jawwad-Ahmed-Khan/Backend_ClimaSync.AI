# Data Model: NGO Registration

## Entities

### `User` (Module: `users`)
| Field | Type | Constraint |
|---|---|---|
| `user_id` | UUID | PK, default: `uuid_generate_v4()` |
| `email` | String | Unique, Not Null |
| `password_hash` | String | Not Null |
| `role` | Enum (`admin`, `ngo_user`) | Not Null |
| `is_active` | Boolean | Default: `True` |
| `email_verified` | Boolean | Default: `False` |
| `email_verified_at` | DateTime | Nullable |
| `created_at` | DateTime | Not Null |
| `updated_at` | DateTime | Not Null |

### `AuthVerificationToken` (Module: `auth`)
| Field | Type | Constraint |
|---|---|---|
| `verification_token_id` | UUID | PK |
| `user_id` | UUID | FK -> `users.user_id` |
| `email` | String | Not Null |
| `purpose` | Enum (`email_verification`) | Not Null |
| `token_hash` | String | Not Null |
| `expires_at` | DateTime | Not Null |
| `used_at` | DateTime | Nullable |
| `revoked_at` | DateTime | Nullable |
| `attempts_count` | Integer | Default: 0 |
| `max_attempts` | Integer | Default: 5 |

### `NgoProfile` (Module: `ngo`)
| Field | Type | Constraint |
|---|---|---|
| `ngo_id` | UUID | PK, FK -> `users.user_id` |
| `org_name` | String | Not Null |
| `registration_number` | String | Unique, Not Null (starts with `TEMP-`) |
| `verification_status` | Enum (`pending`, `verified`, `suspended`) | Default: `pending` |
| `created_at` | DateTime | Not Null |
| `updated_at` | DateTime | Not Null |

### `NgoResource` (Module: `ngo`)
| Field | Type | Constraint |
|---|---|---|
| `ngo_id` | UUID | PK, FK -> `ngo_profiles.ngo_id` |
| `ambulances` | Integer | Default: 0 |
| `rescue_boats` | Integer | Default: 0 |
| `trucks` | Integer | Default: 0 |
| `four_wheel_vehicles` | Integer | Default: 0 |
| `cranes` | Integer | Default: 0 |
| `doctors` | Integer | Default: 0 |
| `paramedics` | Integer | Default: 0 |
| `rescue_divers` | Integer | Default: 0 |
| `volunteers_available` | Integer | Default: 0 |
| `food_packets_capacity` | Integer | Default: 0 |
| `shelter_capacity` | Integer | Default: 0 |

### `AuthRefreshToken` (Module: `auth`)
| Field | Type | Constraint |
|---|---|---|
| `refresh_token_id` | UUID | PK |
| `user_id` | UUID | FK -> `users.user_id` |
| `token_hash` | String | Not Null |
| `expires_at` | DateTime | Not Null |
| `ip_address` | String | Nullable |
| `user_agent` | String | Nullable |
| `revoked_at` | DateTime | Nullable |

## Relationships
- `User` (1) -> (1) `NgoProfile`
- `NgoProfile` (1) -> (1) `NgoResource`
- `User` (1) -> (N) `AuthVerificationToken`
- `User` (1) -> (N) `AuthRefreshToken`
