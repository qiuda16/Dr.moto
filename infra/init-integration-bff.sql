SELECT 'CREATE DATABASE bff'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'bff')
\gexec
