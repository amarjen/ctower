install-editable:
	python -m pip install --editable .

test:
	py.test tests

pdf:
	enscript -C -G2rE ctower/main.py ctower/lib/entities.py ctower/lib/settings.py -o program.ps
	ps2pdf program.ps
	rm program.ps

.PHONY: install-editable test pdf
