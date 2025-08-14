# validate_fsa029.py
from __future__ import annotations
from pathlib import Path
import sys
from lxml import etree as ET
from argparse import Namespace

XS_NS = "http://www.w3.org/2001/XMLSchema"
NS = {"xs": XS_NS}


def make_secure_parser() -> ET.XMLParser:
    '''
        Ensures secure parsing of XML documents against realistic risks even with local files, specifically:
            - XXE (XML External Entity) attacks
            - SSRF (Server-Side Request Forgery)
            - Billion Laughs (Entity Expansion DoS)
            - Memory exhaustion / CPU abuse
        `no_network` shouldn't be necessary with the `load_dtd` and `resolve_entities` flags but is added for completion
    '''
    return ET.XMLParser(
        load_dtd=False,
        no_network=True,
        resolve_entities=False,
        huge_tree=False,
    )

def load_xml(path: Path, kind: str) -> ET._ElementTree:
    try:
        return ET.parse(str(path), parser=make_secure_parser())
    except ET.XMLSyntaxError as e:
        raise RuntimeError(f"[Error] {kind} is not well-formed XML: {e}") from e
    except OSError as e:
        raise RuntimeError(f"[Error] Cannot read {kind} at {path}: {e}") from e

# We're mimicking the effect of a real-world environment where schemas come from an external regulator, so we can't alter the official files
def rewrite_schema_imports_in_memory(xsd_tree: ET._ElementTree, schema_dir: Path) -> ET._ElementTree:
    root = xsd_tree.getroot()

    # Locations where external sources can be defined to pull in other schema files
    for tag in ("import", "include", "redefine"):
        for node in root.findall(f".//xs:{tag}", namespaces=NS):
            loc = node.get("schemaLocation")
            
            if not loc:
                continue

            file_name = Path(loc).name
            local_uri = (schema_dir / file_name).resolve().as_uri()

            # We over-index for safety by accounting for any references to CommonTypes and re-routing to the local path. We could just assign all of the schemaLocations straight to the local path immediately without checking.
            if "/CommonTypes/v14/" in loc or "\\CommonTypes\\v14\\" in loc:
                node.set("schemaLocation", local_uri)
                continue

    # Defensive checking, if anything slips through based on the initial /CommonTypes/v14/ 
    for tag in ("import", "include", "redefine"):
        for node in root.findall(f".//xs:{tag}", namespaces=NS):
            loc = node.get("schemaLocation") or ""
            if "/CommonTypes/v14/" in loc or "\\CommonTypes\\v14\\" in loc:
                raise RuntimeError("[Error] '/CommonTypes/v14/' still present after rewrite.")
    return xsd_tree

def compile_schema(xsd_tree: ET._ElementTree) -> ET.XMLSchema:
    parser = make_secure_parser()

    # We get all of the re-writes we made earlier into the new version here
    xsd_bytes = ET.tostring(xsd_tree, xml_declaration=True, encoding="utf-8")
    try:
        # Re-parse to create a fresh element rree
        xsd_doc = ET.fromstring(xsd_bytes, parser=parser)
        return ET.XMLSchema(xsd_doc)
    except ET.XMLSchemaParseError as e:
        lines = [f"[Error] Schema compilation failed ({len(e.error_log)} issue(s)):"]
        for i, entry in enumerate(e.error_log, 1):
            lines.append(f"  {i}. Line {entry.line}, Col {entry.column}: {entry.message}")
        raise RuntimeError("\n".join(lines)) from e

def validate(args: Namespace) -> int:
    # We build the paths to the files and directories based on the input arguments given in the CLI
    schema_dir = Path(args.schema_dir)
    submission = Path(args.submission)
    fsa_xsd = schema_dir / "FSA029-Schema.xsd"
    ct_xsd  = schema_dir / "CommonTypes-Schema.xsd"

    # check for forbidden '/CommonTypes/v14/' in any location
    forbidden_parts = ("/CommonTypes/v14/", "\\CommonTypes\\v14\\")
    def _contains_forbidden(p: Path) -> bool:
        return any(f in str(p) for f in forbidden_parts)
    if any(_contains_forbidden(p) for p in (schema_dir, submission)):
        print("[ERROR] File locations must not contain '/CommonTypes/v14/'.", file=sys.stderr); return 2

    # If there was a mistake while invoking, they will be raised here
    if not schema_dir.is_dir():
        print(f"[ERROR] Not a directory: {schema_dir}", file=sys.stderr); return 2
    if not fsa_xsd.is_file():
        print(f"[ERROR] Missing: {fsa_xsd}", file=sys.stderr); return 2
    if not ct_xsd.is_file():
        print(f"[ERROR] Missing: {ct_xsd}", file=sys.stderr); return 2
    if not submission.is_file():
        print(f"[ERROR] Missing: {submission}", file=sys.stderr); return 2

    try:
        xsd_tree    = load_xml(fsa_xsd, kind="Main XSD")
        _           = load_xml(ct_xsd,  kind="CommonTypes XSD")
        xml_doc     = load_xml(submission, kind="Submission")
    except RuntimeError as e:
        print(f"[ERROR] {e}", file=sys.stderr); return 2

    print(f"[OK] Loaded XSDs & submission securely.")

    try:
        rewritten = rewrite_schema_imports_in_memory(xsd_tree, schema_dir)
    except RuntimeError as e:
        print(f"[ERROR] {e}", file=sys.stderr); return 2

    try:
        schema = compile_schema(rewritten)
    except RuntimeError as e:
        print(f"[ERROR] {e}", file=sys.stderr); return 2

    # Final flag to check if the file was validated
    ok = schema.validate(xml_doc)
    if ok:
        print("[OK] Submission conforms to the FSA029 schema.")
        return 0
    else:
        print("[Error] Issues:")
        for i, entry in enumerate(schema.error_log, 1):
            print(f"  {i:>2}. Line {entry.line}, Col {entry.column}: {entry.message}")
        return 1


if __name__ == "__main__":
    # Using CLI for the flexibility to run in multiple environments along with being able to change the context of the schema directory along with the submission file.
    import argparse
    p = argparse.ArgumentParser(description="Validate an FSA029 submission against local schemas")
    p.add_argument("schema_dir", help="Folder containing schema directories")
    p.add_argument("submission", help="Path to the FSA029 XML submission")
    args = p.parse_args()

    # Based on the code returned by validate 0 for success and non-zero indicating some kind of error. 2 in our code indicates a file or directory problem.
    sys.exit(validate(args))
