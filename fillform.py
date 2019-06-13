#!/usr/bin/env python3
import fitz
import argparse
import os
import re

argparser = argparse.ArgumentParser()
argparser.add_argument("pdffile", help="PDF form to fill")
argparser.add_argument("--input", help="text file with the field info")
argparser.add_argument("--outfile", default=None, help="filename of the output file")
argparser.add_argument("--enumerate", default=False, action="store_true", help="Number all fields in the pdf")
argparser.add_argument("--fontsize", type=float, help="Fontsize of form fields")
args = argparser.parse_args()

# maximum number of fields to process
N_max_fields = 1000

def update_field(annot, value, force_text=False, fontsize=None):
    # returns True if a field is a checkbox (needed for manual fix)
    # return False otherwise
    w = annot.widget
    if force_text and annot.widget.field_type == 1:
        old_w = annot.widget
        w = fitz.Widget()
        w.rect = old_w.rect
        w.field_type = fitz.ANNOT_WG_TEXT
        w.field_name = old_w.field_name+"_number"
        w.field_value = value
        annot.parent.addWidget(w)
        return
    if w.field_type == 1: # check box
        if value != "":
            w.field_value = value
            annot.setBorder({'width': -1.0, 'dashes': [], 'style': None})
            #w.field_flags = 1
            return True
    if w.field_type == 3: # text field
        w.field_value = value
        if fontsize is not None:
            w.text_fontsize = fontsize

    annot.updateWidget(w)
    #annot.update()
    return False

def get_annotations(page, inds=None):
    annots = []
    annot = page.firstAnnot
    # build a list with annotations
    for n in range(N_max_fields):
        if annot is None:
            break
        if inds is None or n in inds:
            annots.append(annot)
        annot = annot.next
    return annots

def enumerate_fields(pdf_file, fontsize=None, outfile=None):
    doc = fitz.open(pdf_file)
    page = doc[0]

    annots = get_annotations(page)
    if fontsize == "first":
        fontsize = annots[0].widget.text_fontsize


    # update fields
    for n,a in enumerate(annots):
        update_field(a, "{}".format(n), force_text=True,fontsize=fontsize)

    # save the pdf
    if outfile:
        new_file = outfile
    else:
        p = os.path.splitext(pdf_file)
        new_file = p[0]+'_numbered'+p[1]
    doc.save(new_file)

def fill_fields(pdf_file, field_file, fontsize=None, outfile=None):
    # parse the text file with field contents
    field_name = []
    field_number = []
    field_content = []
    N_fields = 0
    with open(field_file, "r") as f:
        for line in f:
            if line.strip() == "" or line.strip()[0] == "#":
                continue
            try:
                name, number, content = line.strip().split(maxsplit=2)
                field_name.append(name)
                field_number.append(int(number))
                field_content.append(content)
                N_fields += 1
            except ValueError:
                pass

    # open the pdf
    doc = fitz.open(pdf_file)
    page = doc[0]

    annots = get_annotations(page)
    if fontsize == "first":
        fontsize = annots[0].widget.text_fontsize

    checkboxes = []
    # update fields
    for n in range(N_fields):
        if update_field(annots[field_number[n]], field_content[n], fontsize=fontsize):
            checkboxes.append( field_number[n] )

    # save the pdf
    if outfile:
        new_file = outfile
    else:
        p = os.path.splitext(pdf_file)
        new_file = p[0]+'_filled'+p[1]
    doc.save(new_file)

    # manually tick checkboxes
    import pdfrw
    newdoc = pdfrw.PdfReader(new_file)
    annots = newdoc.pages[0]["/Annots"]
    for n in checkboxes:
        a = annots[n]
        a.AS = "/On"
    pdfrw.PdfWriter(new_file, trailer=newdoc).write()

if args.fontsize:
    fontsize = args.fontsize
else:
    fontsize = "first"

if args.input:
    fill_fields(args.pdffile, args.input, fontsize=fontsize, outfile=args.outfile)
if args.enumerate:
    enumerate_fields(args.pdffile, fontsize=fontsize, outfile=args.outfile)
