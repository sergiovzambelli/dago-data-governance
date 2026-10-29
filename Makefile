KIT := data/Kit_team_hackathon_sfida_5

# zipfile di Python scarta percorsi assoluti e "..": niente zip-slip
data:
	python3 -m zipfile -e info/Kit_team_hackathon_sfida_5.zip data
	python3 -m zipfile -e $(KIT)/validation_set.zip data/validation

.PHONY: data

# misura sul dataset di sviluppo e sul validation set
score:
	python3 -m classifier.pipeline $(KIT)/sviluppo > data/pred_sviluppo.json
	python3 -m classifier.scorer $(KIT)/Etichette_sviluppo.csv data/pred_sviluppo.json
	python3 -m classifier.pipeline data/validation/valutazione > data/pred_validation.json
	python3 -m classifier.scorer data/validation/Etichette_valutazione_RISERVATO.csv data/pred_validation.json

.PHONY: score
