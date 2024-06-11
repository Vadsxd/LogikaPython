DROP TABLE IF EXISTS archive_types;
DROP TABLE IF EXISTS buses;
DROP TABLE IF EXISTS channels;
DROP TABLE IF EXISTS data_types;
DROP TABLE IF EXISTS devices;
DROP TABLE IF EXISTS l4_archive_fields;
DROP TABLE IF EXISTS l4_archives;
DROP TABLE IF EXISTS l4_tags;
DROP TABLE IF EXISTS l4_types;
DROP TABLE IF EXISTS m4_archive_fields;
DROP TABLE IF EXISTS m4_archives;
DROP TABLE IF EXISTS m4_tags;
DROP TABLE IF EXISTS tag_kinds;
DROP TABLE IF EXISTS vars;
DROP TABLE IF EXISTS x6_archive_fields;
DROP TABLE IF EXISTS x6_tag_type;
DROP TABLE IF EXISTS x6_tags;
DROP TABLE IF EXISTS x6_archives;


CREATE TABLE IF NOT EXISTS archive_types(
    typing TEXT NOT NULL,
    description TEXT NOT NULL,
    comment TEXT
);

CREATE TABLE IF NOT EXISTS buses(
    key TEXT NOT NULL,
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS channels(
    device TEXT NOT NULL,
    key TEXT NOT NULL,
    description TEXT NOT NULL,
    start INTEGER NOT NULL,
    count INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS data_types(
    name TEXT NOT NULL,
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS devices(
    key TEXT NOT NULL,
    bus TEXT NOT NULL,
    m4 INTEGER,
    description TEXT NOT NULL,
    media TEXT NOT NULL,
    pipes INTEGER,
    consumers INTEGER,
    aux_no INTEGER
);

CREATE TABLE IF NOT EXISTS l4_archive_fields(
    device TEXT NOT NULL,
    archive_type TEXT NOT NULL,
    field_offset INTEGER NOT NULL,
    name TEXT NOT NULL,
    internal_type TEXT NOT NULL,
    data_type TEXT NOT NULL,
    description TEXT NOT NULL,
    var_t TEXT NOT NULL,
    units TEXT,
    db_type TEXT
);

CREATE TABLE IF NOT EXISTS l4_archives(
    device TEXT NOT NULL,
    archive_type TEXT NOT NULL,
    channel TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    record_type TEXT NOT NULL,
    record_size INTEGER NOT NULL,
    count INTEGER NOT NULL,
    index_1 INTEGER NOT NULL,
    headers_1 INTEGER,
    index_2 INTEGER,
    headers_2 INTEGER,
    records_2 INTEGER
);

CREATE TABLE IF NOT EXISTS l4_tags(
    device TEXT NOT NULL,
    channel TEXT NOT NULL,
    ordinal INTEGER NOT NULL,
    kind TEXT NOT NULL,
    basic INTEGER NOT NULL,
    data_type TEXT NOT NULL,
    db_type TEXT,
    update_rate INTEGER NOT NULL,
    name TEXT NOT NULL,
    display_format TEXT,
    description TEXT NOT NULL,
    var_t TEXT,
    units TEXT,
    internal_type TEXT NOT NULL,
    in_ram INTEGER NOT NULL,
    address INTEGER,
    channel_offset INTEGER,
    addon INTEGER,
    addon_offset INTEGER,
    ranging TEXT,
    description_ex TEXT
);

CREATE TABLE IF NOT EXISTS l4_types(
    typing TEXT NOT NULL,
    description TEXT NOT NULL,
    comment TEXT
);

CREATE TABLE IF NOT EXISTS m4_archive_fields(
    device TEXT NOT NULL,
    archive_type TEXT NOT NULL,
    'index' INTEGER NOT NULL,
    name TEXT NOT NULL,
    data_type TEXT NOT NULL,
    description TEXT NOT NULL,
    var_t TEXT NOT NULL,
    units TEXT,
    db_type TEXT,
    display_format TEXT
);

CREATE TABLE IF NOT EXISTS m4_archives(
    device TEXT NOT NULL,
    archive_type TEXT NOT NULL,
    channel TEXT NOT NULL,
    record_type TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    capacity INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS m4_tags(
    device TEXT NOT NULL,
    channel TEXT NOT NULL,
    ordinal INTEGER NOT NULL,
    kind TEXT NOT NULL,
    basic INTEGER NOT NULL,
    data_type TEXT NOT NULL,
    db_type TEXT,
    update_rate INTEGER NOT NULL,
    name TEXT NOT NULL,
    display_format TEXT,
    description TEXT NOT NULL,
    var_t TEXT,
    units TEXT,
    ranging TEXT,
    description_ex TEXT
);

CREATE TABLE IF NOT EXISTS tag_kinds(
    kind TEXT NOT NULL,
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vars(
    var_t TEXT NOT NULL,
    desc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS x6_archive_fields(
    device TEXT NOT NULL,
    archive_type TEXT NOT NULL,
    channel TEXT NOT NULL,
    ordinal TEXT NOT NULL,
    data_type TEXT NOT NULL,
    db_type TEXT,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    var_t TEXT NOT NULL,
    start_index INTEGER,
    count INTEGER,
    depth INTEGER,
    _comment TEXT
);

CREATE TABLE IF NOT EXISTS x6_archives(
    device TEXT NOT NULL,
    archive_type TEXT NOT NULL,
    ordinal TEXT NOT NULL,
    record_type TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    capacity INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS x6_tags(
    device TEXT NOT NULL,
    channel TEXT NOT NULL,
    ordinal INTEGER NOT NULL,
    'index' INTEGER,
    typing TEXT NOT NULL,
    kind TEXT,
    basic INTEGER NOT NULL,
    data_type TEXT,
    update_rate INTEGER NOT NULL,
    name TEXT,
    description TEXT NOT NULL,
    var_t TEXT,
    count INTEGER,
    ranging TEXT,
    description_ex TEXT
);

CREATE TABLE IF NOT EXISTS x6_tag_type(
    typing TEXT NOT NULL
);

INSERT INTO x6_tag_type (typing)
VALUES ('array'), ('structure'), ('tag');

INSERT INTO buses (key, description)
VALUES ('RSbus', 'один или несколько приборов 94x-74x объединенных в сеть'),
       ('SPbus', 'шина приборов поддерживающих протокол СПСеть');

INSERT INTO archive_types (typing, description, comment)
VALUES ('Control', 'контрольный архив (M4, тотальные + текущие)', null),
       ('Day', 'суточный архив', null),
       ('Decade', 'декадный архив', null),
       ('DiagsLog', 'асинхронный архив ДС', null),
       ('ErrorsLog', 'асинхронный архив НС', null),
       ('Hours', 'часовой архив', null),
       ('Month', 'месячный архив', null),
       ('ParamsLog', 'асинхронный архив изменений БД', null),
       ('PowerLog', 'асинхронный архив перерывов питания', null),
       ('Turn', 'сменный архив (асинхронный)', null),
       ('Minute', 'минутный архив', null),
       ('HalfHour', '[полу]часовой архив', null);

INSERT INTO data_types (name, description)
VALUES ('Int32', 'Целое со знаком (32-bit)'),
       ('Double', 'Вещественное двойной точности (64-bit)'),
       ('String', 'Строка'),
       ('String[]', 'Массив строк'),
       ('Byte[]', 'массив u8'),
       ('Single', 'Вещественное число (32-bit)'),
       ('Object[]', 'Массив переменных разного типа (архивный срез)'),
       ('Int32[]', 'массив номеров НС');

INSERT INTO tag_kinds (kind, description)
VALUES ('Info', 'информация о приборе (read-only)'),
       ('Parameter', 'настроечный параметр'),
       ('Realtime', 'вычисленное прибором значение (результат измерений)'),
       ('TotalCtr', 'тотальный счетчик');

INSERT INTO vars (var_t, desc)
VALUES ('auxInt', 'int общего назначения'),
       ('AVG', 'не пойми что, в итоговых - усреднять'),
       ('dP', 'перепад давления'),
       ('G', 'расход'),
       ('M', 'масса'),
       ('NS', 'сборка флагов (напр. НС)'),
       ('P', 'давление'),
       ('SP', 'схема потребления, обычно integer'),
       ('T', 'температура'),
       ('ti', 'интервал времени'),
       ('V', 'объем'),
       ('W', 'энергия');

INSERT INTO l4_types (typing, description, comment)
VALUES ('r32', '32-bit MicroChip float', 'четырехбайтовое вещественное число в формате MicroChip float'),
       ('r32x3', 'тройной MicroChip float', 'для получения значения - все три сложить (тотальные 941)'),
       ('time', 'ЧЧ-ММ-СС (24-bit)', 'время'),
       ('date', 'ГГ-ММ-ДД (24-bit)', 'дата'),
       ('MMDD', 'ММ-ДД-xx-xx', 'дата перехода на летнее/зимнее время'),
       ('dbentry', 'параметр БД приборов x4, строка', 'используется строковое поле структуры "элемент БД"'),
       ('u8', '8-bit unsigned', null),
       ('i32r32', 'int32+microchip float32 во FLASH', 'см. тотальный счетчик прибора 942'),
       ('NSrecord', 'запись архива НС', 'см. архив НС 942, 741'),
       ('MMHH', 'MM, HH', 'минуты, часы (941, ТО)'),
       ('bitArray8', 'битовая строка, 8 бит', 'НС по общему каналу 941, 942, 943'),
       ('bitArray24', 'битовая строка, 24 бит', 'НС СПТ941.10 (общий + ТВ)'),
       ('bitArray32', 'битовая строка, 32 бит', 'НС СПГ741'),
       ('bitArray16', 'битовая строка, 16 бит', 'НС по ТВ 942, 943, смещение индекса битов +8'),
       ('u24', '24-bit unsigned', 'серийный (заводской) номер прибора'),
       ('modelChar', 'char[1]', 'модель прибора'),
       ('dbentry_byte', 'параметр БД приборов x4, байт', 'используется бинарное поле структуры "элемент БД", LSB');