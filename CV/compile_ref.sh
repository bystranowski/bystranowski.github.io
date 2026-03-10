#!/bin/bash

rm *.aux *.bbl *.bcf *.blg
pdflatex CVnew.tex          # or xelatex if you switch back later
biber CVnew
pdflatex CVnew.tex
pdflatex CVnew.tex
cp CVnew.pdf ../assets/Piotr_Bystranowski_CV.pdf
