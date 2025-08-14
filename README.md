# FSA029 XML Schema Validator

This is to provide instructions on how to run the script for the XML Challenge

---

## Requirements

- **Python**: 3.12+
- **Dependencies**:  
  Install dependencies with:
  ```bash
  python -m install -r requirements.txt
  ```

### Note: This project used a virtual environment

The virtual environment used Python version 3.12 and was created using:

```bash
python -m venv .venv
```

and instantiated using:

Windows:
```bash
.venv/Scripts/Activate.ps1
```

macOS/Linux:
```bash
source .venv/bin/activate
```

---

## Expected Folder Structure

```
your_schema_dir/
├── FSA029-Schema.xsd
├── CommonTypes-Schema.xsd
samples/
└── FSA029-Sample-Valid.xml
```

**Important**:
- Both `FSA029-Schema.xsd` and `CommonTypes-Schema.xsd` **must** be in the same folder.
- The folder path must **not** contain `/CommonTypes/v14/` (or `\CommonTypes\v14\` on Windows) or the script will 
throw an error

---

## Usage

From the command line:

```bash
python validate_fsa029.py <schema_dir> <submission_file>
```

Example:
```bash
python validate_fsa029.py schemas samples/FSA029-Sample-Valid.xml
```

Where:
- `schema_dir` is the directory containing `FSA029-Schema.xsd` and `CommonTypes-Schema.xsd`.
- `submission_file` is the XML submission to validate.

---

## Expected Output

If validation passes:
```
[OK] Loaded XSDs & submission securely.
[OK] Submission conforms to the FSA029 schema.
```

---

## Reflections on `FSA029-SampleFull.xml`

(a) **Cause of failure**  
`FSA029-SampleFull.xml` fails with the following error:
```
[OK] Loaded XSDs & submission securely.
[Error] Issues:
   1. Line 102, Col 0: Element '{urn:fsa-gov-uk:MER:FSA029:4}PartnershipsSoleTraders': This element is not expected.
```

meaning that the sampleFull file is referencing an element `PartnershipsSoleTraders` that does not exist in the schema 
definition we provided for validation, or at least not in the position it was found. 


(b) **How to fix it**  
The validator is checking through the XML file and on some parent element, it expected to see certain contents according
to the schema but ended up finding something incorrect. We can could check the .xsd for the parent and then we can check
how that element is failing, by name, order, occurence, etc and then update the XML based on that error similar to 
how we handled changing the `schemaLocation` when accounting for `/CommonTypes/v14/`

(c) **Why the regulator included an invalid example**  
If there was some change in the past to the file structure, the regulator may be showing that the files could contain 
unexpected fields (legacy fields?) that we will need to handle. They might also be common mistakes, and help 
developers to understand these validation failures.
---

## Notes

- This script modifies schema import paths **only in memory** during runtime.
- The original `.xsd` files remain unchanged.
- All schema loading is done to account for security.
