create extension if not exists vector;

create table if not exists recipe (
    id integer primary key,
    name text not null,
    description text,
    ingredients_raw text[] not null,
    steps text[] not null,
    servings numeric,
    serving_size text,
    -- Diets Claude judged the recipe fits ("yes" verdicts), filled by classify_diet.py
    diet_tags text[] not null default '{}',
    -- food.com photo URL; null when the recipe has no photo or fetch_images.py has not run yet
    image text,
    -- Cached result of nutrition.analyze(); null until someone requests the analysis
    nutrition jsonb,
    embed_text text not null,
    embedding vector(1024) not null
);

create table if not exists app_user (
    id serial primary key,
    email text not null unique,
    -- "scrypt$<salt hex>$<digest hex>", see auth.py
    password_hash text not null,
    -- Unlocked with the shared ACCESS_CODE; required for search, recipes and nutrition
    has_access boolean not null default false,
    created_at timestamptz not null default now()
);

create table if not exists user_session (
    -- SHA-256 of the cookie token; the token itself is never stored
    token_hash text primary key,
    user_id integer not null references app_user (id) on delete cascade,
    expires_at timestamptz not null
);

create table if not exists favorite (
    user_id integer not null references app_user (id) on delete cascade,
    recipe_id integer not null references recipe (id) on delete cascade,
    created_at timestamptz not null default now(),
    primary key (user_id, recipe_id)
);

-- Dietary filters use the @> (contains) operator on diet_tags
create index if not exists recipe_diet_tags_idx on recipe using gin (diet_tags);
