#!/usr/bin/env sh
# Starts the backend development server once backend implementation begins.
uvicorn app.main:app --reload
