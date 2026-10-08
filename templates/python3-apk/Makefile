SHELL := /usr/bin/env bash
PYTHON ?= python3
BUILD_MODE ?= debug

.PHONY: doctor install validate build clean

doctor:
	@command -v $(PYTHON)
	@command -v java
	@command -v gcc
	@command -v make
	@command -v cmake
	@command -v p4a
	@test -n "$$ANDROIDSDK" -o -n "$$ANDROID_SDK_ROOT"
	@test -n "$$ANDROIDNDK" -o -n "$$ANDROID_NDK_HOME"
	@echo APK_BUILD_DOCTOR_GREEN

install:
	$(PYTHON) -m pip install --requirement requirements-build.txt

validate:
	$(PYTHON) -m py_compile app/main.py sanity.py
	@grep -q '^--bootstrap webview$$' .p4a
	@grep -q '^--arch arm64-v8a$$' .p4a
	@echo APK_TEMPLATE_CONFIG_GREEN

build: validate
	BUILD_MODE=$(BUILD_MODE) ./build-apk.sh

clean:
	-rm -rf dist .buildozer build
	-p4a clean_builds
	-p4a clean_dists
