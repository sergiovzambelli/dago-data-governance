KIT := data/Kit_team_hackathon_sfida_5

# zipfile di Python scarta percorsi assoluti e "..": niente zip-slip
data:
	python3 -m zipfile -e info/Kit_team_hackathon_sfida_5.zip data
	python3 -m zipfile -e $(KIT)/validation_set.zip data/validation

.PHONY: data
