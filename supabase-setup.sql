-- ============================================
-- Schema para Dashboard de Guiones — SFRE
-- Correr en Supabase SQL Editor (supabase.com → SQL Editor → New Query)
-- ============================================

-- 1. Tabla de guiones (migrada del array JS)
CREATE TABLE guiones (
    id TEXT PRIMARY KEY,
    tema TEXT NOT NULL,
    titulo TEXT NOT NULL,
    angulo TEXT NOT NULL CHECK (angulo IN ('prob','prod','sol','con','aut','pred','comp','hist')),
    tipo TEXT DEFAULT 'organico' CHECK (tipo IN ('organico','ads')),
    hook TEXT NOT NULL,
    texto TEXT NOT NULL,
    screen TEXT DEFAULT '',
    caption_ig TEXT DEFAULT '',
    caption_tk TEXT DEFAULT '',
    fuentes TEXT DEFAULT '',
    status TEXT DEFAULT 'listo' CHECK (status IN ('listo','filmado','publicado','descartado')),
    rating INTEGER DEFAULT 0 CHECK (rating BETWEEN 0 AND 5),
    notas TEXT DEFAULT '',
    semana TEXT DEFAULT '',
    orden INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Tabla de ideas
CREATE TABLE ideas (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    autor TEXT DEFAULT 'Santiago',
    angulo TEXT DEFAULT '' CHECK (angulo IN ('','prob','prod','sol','con','aut','pred','comp','hist')),
    tema TEXT NOT NULL,
    detalle TEXT DEFAULT '',
    estado TEXT DEFAULT 'propuesta' CHECK (estado IN ('propuesta','aprobada','escrita','descartada')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Tabla de newsletter / tendencias
CREATE TABLE newsletter (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    titulo TEXT NOT NULL,
    hook_propuesto TEXT DEFAULT '',
    angulo TEXT DEFAULT '',
    dato_duro TEXT DEFAULT '',
    fuente_url TEXT DEFAULT '',
    por_que_pega TEXT DEFAULT '',
    convertido BOOLEAN DEFAULT FALSE,
    guion_id TEXT REFERENCES guiones(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Trigger para updated_at automático en guiones
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER guiones_updated_at
    BEFORE UPDATE ON guiones
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_column();

-- 5. Row Level Security (todos los usuarios autenticados tienen acceso completo)
ALTER TABLE guiones ENABLE ROW LEVEL SECURITY;
ALTER TABLE ideas ENABLE ROW LEVEL SECURITY;
ALTER TABLE newsletter ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated users full access on guiones"
    ON guiones FOR ALL
    USING (auth.role() = 'authenticated')
    WITH CHECK (auth.role() = 'authenticated');

CREATE POLICY "Authenticated users full access on ideas"
    ON ideas FOR ALL
    USING (auth.role() = 'authenticated')
    WITH CHECK (auth.role() = 'authenticated');

CREATE POLICY "Authenticated users full access on newsletter"
    ON newsletter FOR ALL
    USING (auth.role() = 'authenticated')
    WITH CHECK (auth.role() = 'authenticated');

-- 6. Índices útiles
CREATE INDEX idx_guiones_angulo ON guiones(angulo);
CREATE INDEX idx_guiones_tema ON guiones(tema);
CREATE INDEX idx_guiones_tipo ON guiones(tipo);
CREATE INDEX idx_guiones_status ON guiones(status);
CREATE INDEX idx_guiones_semana ON guiones(semana);
CREATE INDEX idx_ideas_estado ON ideas(estado);
CREATE INDEX idx_newsletter_convertido ON newsletter(convertido);
