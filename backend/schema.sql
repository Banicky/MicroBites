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
    embed_text text not null,
    embedding vector(1024) not null
);

-- Dietary filters use the @> (contains) operator on diet_tags
create index if not exists recipe_diet_tags_idx on recipe using gin (diet_tags);
