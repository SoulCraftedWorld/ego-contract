.PHONY: cpp python all clean

all: cpp python

cpp:
	./scripts/gen_cpp.sh

python:
	./scripts/gen_python.sh

clean:
	rm -rf generated
