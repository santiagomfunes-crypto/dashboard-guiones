-- Migration: 011_propiedades_mercado_add_argenprop
-- Amplía el CHECK constraint de fuente para incluir argenprop y zonaprop
-- Ref: SAN-247

ALTER TABLE public.propiedades_mercado
    DROP CONSTRAINT IF EXISTS propiedades_mercado_fuente_check;

ALTER TABLE public.propiedades_mercado
    ADD CONSTRAINT propiedades_mercado_fuente_check
    CHECK (fuente IN ('mercadolibre', 'zonaprop', 'casasdehoy', 'argenprop'));
