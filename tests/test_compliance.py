import pytest

from classifier.compliance import check, load_permissions

REC = {
    "codice": "T-PER-07",
    "percorsi": ["fileserver/Personale/Permessi"],
    "categorie_dichiarate": {"SALUTE"},
    "diffusione": False,
}


@pytest.fixture
def perms(tmp_path):
    p = tmp_path / "permessi.csv"
    p.write_text("cartella;gruppi_con_accesso\n"
                 "fileserver/Personale/Permessi;GG_RU_PRESENZE\n"
                 "fileserver/Personale/Varie;GG_RU_PRESENZE, GG_TUTTI_DIPENDENTI\n"
                 "fileserver/Pubblicazioni;GG_SEGRETERIA\n", encoding="utf-8")
    return load_permissions(p)


def test_document_matching_its_record_is_compliant(perms):
    assert check(REC, "fileserver/Personale/Permessi/a.pdf", ["SALUTE"], perms) == []


def test_undeclared_category(perms):
    assert check(REC, "fileserver/Personale/Permessi/a.pdf", ["SALUTE", "GIUDIZIARI"], perms) == \
        ["CATEGORIA_NON_DICHIARATA"]


def test_folder_not_declared_and_open_to_all_employees(perms):
    assert check(REC, "fileserver/Personale/Varie/scan.pdf", [], perms) == \
        ["LUOGO_NON_DICHIARATO", "ACCESSO_ECCESSIVO"]


def test_folder_prefix_must_match_whole_segments(perms):
    assert "LUOGO_NON_DICHIARATO" in check(REC, "fileserver/Personale/PermessiVecchi/a.pdf", [], perms)


def test_most_specific_folder_decides_access(tmp_path):
    p = tmp_path / "permessi.csv"
    p.write_text("cartella;gruppi_con_accesso\nfileserver;GG_TUTTI_DIPENDENTI\n"
                 "fileserver/Personale/Permessi;GG_RU_PRESENZE\n", encoding="utf-8")
    assert check(REC, "fileserver/Personale/Permessi/a.pdf", [], load_permissions(p)) == []


def test_published_folder_needs_diffusion_in_record(perms):
    assert check({**REC, "percorsi": ["fileserver/Pubblicazioni"]}, "fileserver/Pubblicazioni/albo/g.xlsx",
                 [], perms) == ["DIFFUSIONE_NON_PREVISTA"]


def test_published_document_with_special_category_is_never_allowed(perms):
    rec = {**REC, "percorsi": ["fileserver/Pubblicazioni"], "diffusione": True}
    assert check(rec, "fileserver/Pubblicazioni/albo/g.xlsx", ["SALUTE"], perms) == ["DIFFUSIONE_NON_PREVISTA"]
    assert check(rec, "fileserver/Pubblicazioni/albo/g.xlsx", [], perms) == []


def test_permissions_without_required_columns_are_rejected(tmp_path):
    p = tmp_path / "permessi.csv"
    p.write_text("cartella;altro\nx;y\n", encoding="utf-8")
    with pytest.raises(ValueError, match="gruppi_con_accesso"):
        load_permissions(p)
