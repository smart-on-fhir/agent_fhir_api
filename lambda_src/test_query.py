import importlib.util
import os
from pathlib import Path

from lambda_src import query


def test_should_get_all_patients(monkeypatch):
    query.local_root =  "./test_data/"
    query.fhir_data_path =  "./test_data/"

    con = query.create_local_db_con()
    result = query.get_fhir_data(con, "patient", [], [], 0, 1000)

    assert len(result) == 5

def test_should_paginate_patients(monkeypatch):
    query.local_root =  "./test_data/"
    query.fhir_data_path =  "./test_data/"

    con = query.create_local_db_con()
    result = query.get_fhir_data(con, "patient", [], [], 0, 2)

    assert len(result) == 2

def test_should_get_patients_with_fields(monkeypatch):
    query.local_root =  "./test_data/"
    query.fhir_data_path =  "./test_data/"

    con = query.create_local_db_con()
    result = query.get_fhir_data(con, "patient", ["id"], [], 0, 1000)
    assert [{"id": "3"}, {"id": "5"}, {"id": "2"}, {"id": "4"}, {"id": "1"}] == result

def test_should_get_patients_with_fields_and_filters(monkeypatch):
    query.local_root =  "./test_data/"
    query.fhir_data_path =  "./test_data/"

    con = query.create_local_db_con()
    result = query.get_fhir_data(con, "patient", ["id"], ["1", "2", "3"], 0, 1000)
    assert [{"id": "3"}, {"id": "2"}, {"id": "1"}] == result

def test_should_get_episode_of_care(monkeypatch):
    query.local_root =  "./test_data/"
    query.fhir_data_path =  "./test_data/"

    con = query.create_local_db_con()
    result = query.get_fhir_data(con, "episodeofcare", ["id"], [], 0, 1000)
    assert len(result) == 2

def test_should_get_medication_request(monkeypatch):
    query.local_root =  "./test_data/"
    query.fhir_data_path =  "./test_data/"

    con = query.create_local_db_con()
    result = query.get_fhir_data(con, "medicationrequest", ["id"], [], 0, 1000)
    assert len(result) == 2