# create table if not exists recipe (
# 	id integer primary key,
# 	title text not null,
# 	image text,
# 	ingredients text[] not null,
# 	steps text[] not null,
# 	servings numeric,
# 	serving_size_g integer,
# 	embed_text text not null,
#   tags text[] not null default '{}',
# 	embedding vector(1024) not null
# )