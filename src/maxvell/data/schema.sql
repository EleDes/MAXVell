CREATE TABLE devices (device_group TEXT PRIMARY KEY, cfm_class TEXT, cfm_bits INTEGER,
    ufm_bits INTEGER, lab_count INTEGER) WITHOUT ROWID;
CREATE TABLE mapping_results (id INTEGER PRIMARY KEY,target TEXT NOT NULL,cfm_class TEXT,region TEXT NOT NULL,bit_offset INTEGER NOT NULL CHECK(bit_offset>=0),field_class TEXT,block_kind TEXT,resource_kind TEXT,block_coord TEXT,signal_name TEXT,polarity TEXT,truth_scope TEXT,usage_class TEXT,transform_status TEXT);
CREATE TABLE metadata (key text primary key,value text not null) without rowid;
CREATE TABLE model_blobs (content_sha256 TEXT PRIMARY KEY, json_bytes INTEGER NOT NULL, zlib_json BLOB NOT NULL) WITHOUT ROWID;
CREATE TABLE model_catalog (target TEXT NOT NULL, kind TEXT NOT NULL, content_sha256 TEXT NOT NULL REFERENCES model_blobs(content_sha256), cfm_bits INTEGER NOT NULL, decoder_module TEXT, decoder_function TEXT, PRIMARY KEY(target,kind)) WITHOUT ROWID;
CREATE INDEX mapping_target_region_offset on mapping_results(target,region,bit_offset);
