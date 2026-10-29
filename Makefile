KIT := data/Kit_team_hackathon_sfida_5

# zipfile di Python scarta percorsi assoluti e "..": niente zip-slip
data:
	python3 -m zipfile -e info/Kit_team_hackathon_sfida_5.zip data
	python3 -m zipfile -e $(KIT)/validation_set.zip data/validation

.PHONY: data

# modello locale facoltativo per i casi dubbi: make score LLM=qwen3:1.7b (o LLM=qwen3:8b); vuoto = spento
LLM ?=

# misura sul dataset di sviluppo e sul validation set
score:
	CLASSIFIER_LLM_MODEL=$(LLM) python3 -m classifier.pipeline $(KIT)/sviluppo $(KIT)/Registro_trattamenti.csv $(KIT)/permessi_cartelle.csv > data/pred_sviluppo.json
	python3 -m classifier.scorer $(KIT)/Etichette_sviluppo.csv data/pred_sviluppo.json
	CLASSIFIER_LLM_MODEL=$(LLM) python3 -m classifier.pipeline data/validation/valutazione $(KIT)/Registro_trattamenti.csv $(KIT)/permessi_cartelle.csv > data/pred_validation.json
	python3 -m classifier.scorer data/validation/Etichette_valutazione_RISERVATO.csv data/pred_validation.json

.PHONY: score
