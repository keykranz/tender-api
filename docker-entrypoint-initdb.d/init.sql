CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Создание таблицы сотрудников (employee)
CREATE TABLE employee (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание типа данных для организации (organization_type)
CREATE TYPE organization_type AS ENUM (
    'IE',  -- Индивидуальный предприниматель
    'LLC', -- Общество с ограниченной ответственностью
    'JSC'  -- Акционерное общество
);

-- Создание таблицы организаций (organization)
CREATE TABLE organization (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    type organization_type,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание таблицы связей между организациями и сотрудниками (organization_responsible)
CREATE TABLE organization_responsible (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organization(id) ON DELETE CASCADE,
    user_id UUID REFERENCES employee(id) ON DELETE CASCADE
);

-- Статус тендера
CREATE TYPE tender_status AS ENUM (
    'CREATED',
    'PUBLISHED',
    'CLOSED'
);

-- Тип тендера
CREATE TYPE service_type_enum AS ENUM (
    'Construction',
    'IT Services',
    'Consulting'
);

-- Создание таблицы тендеров (tender)
CREATE TABLE tender (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tender_root_id UUID NOT NULL,
    organization_id UUID REFERENCES organization(id) ON DELETE CASCADE,
    creator_id UUID REFERENCES employee(id) ON DELETE CASCADE,
    title VARCHAR(100) NOT NULL,
    description TEXT,
    status tender_status DEFAULT 'CREATED',
    service_type service_type_enum NOT NULL,
    version INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- Статус предложения
CREATE TYPE bid_status AS ENUM (
    'CREATED',
    'PUBLISHED',
    'CANCELED',
    'APPROVED',
    'REJECTED'
);

-- Статус решения по предложению
CREATE TYPE decision_status AS ENUM (
    'APPROVED',
    'REJECTED'
);

-- Создание таблицы предложений (bid)
CREATE TABLE bid (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tender_id UUID REFERENCES tender(id) ON DELETE CASCADE,
    bid_root_id UUID NOT NULL,
    organization_id UUID REFERENCES organization(id) ON DELETE CASCADE,
    creator_id UUID REFERENCES employee(id) ON DELETE CASCADE,
    amount NUMERIC(10, 2) NOT NULL,
    title VARCHAR(100) NOT NULL,
    description TEXT,
    status bid_status DEFAULT 'CREATED',
    version INT DEFAULT 1,
    quorum INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание таблицы для решений по предложениям
CREATE TABLE bid_decision (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bid_id UUID REFERENCES bid(id) ON DELETE CASCADE,
    user_id UUID REFERENCES employee(id) ON DELETE CASCADE,
    decision decision_status NOT NULL,
    decision_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание таблицы для отзывов
CREATE TABLE review (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bid_id UUID REFERENCES bid(id) ON DELETE CASCADE,
    reviewer_id UUID REFERENCES employee(id) ON DELETE CASCADE,
    author_id UUID REFERENCES employee(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    rating INT CHECK (rating >= 1 AND rating <= 5),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


INSERT INTO employee (username, first_name, last_name)
VALUES
    ('user1', 'John', 'Doe'),
    ('user2', 'Alice', 'Smith'),
    ('user3', 'Bob', 'Jackson'),
    ('user4', 'Alex', 'Smith');

INSERT INTO organization (name, description, type)
VALUES
    ('Tech Solutions', 'Компания по разработке ПО', 'LLC'),
    ('Business Innovations', 'Консалтинговая фирма', 'JSC');

INSERT INTO organization_responsible (organization_id, user_id)
VALUES
    ((SELECT id FROM organization WHERE name = 'Tech Solutions'), (SELECT id FROM employee WHERE username = 'user1')),
    ((SELECT id FROM organization WHERE name = 'Tech Solutions'), (SELECT id FROM employee WHERE username = 'user2')),
    ((SELECT id FROM organization WHERE name = 'Business Innovations'), (SELECT id FROM employee WHERE username = 'user3')),
    ((SELECT id FROM organization WHERE name = 'Business Innovations'), (SELECT id FROM employee WHERE username = 'user4'));