# PDF/A Reporting
Generate Qweb-pdf documents as PDF/A when required.

## Configuration
After installing this module (on Odoo 15), an option is added to Report-actions, to configure the desired
PDF/A-level. 

That's it!

> For example on report-action `Invoices`, the PDF/A-option can be set to `PDF/A-1b` to send out all sale invoices in this format.

## Usage
Nothing to do.

## How it works
The add-on works as an interceptor on the generation of pdf files from qweb templates. 
When the report has a PDF/A-option set, this option is applied by calling ghostscript, and replacing

## Dependendies
- Ghostscript 9.50 or later
