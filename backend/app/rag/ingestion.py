
import re
from pathlib import Path

from docling.document_converter import DocumentConverter
from docling.chunking import HierarchicalChunker

from backend.app.config import DATASET_DIR
from backend.app.security.manifest_loader import load_manifest


# Create these once and reuse them for every document
CONVERTER = DocumentConverter()
CHUNKER = HierarchicalChunker()


def read_document(file_path: Path):
    result = CONVERTER.convert(str(file_path))
    return result.document


def get_item_type(item) -> str:
    label = getattr(item, "label", "")
    label = getattr(label, "value", label)
    return str(label).lower().split(".")[-1]


def get_page_numbers(items) -> list:
    page_numbers = set()

    for item in items:
        provenance = getattr(item, "prov", None) or []

        for location in provenance:
            page_number = getattr(location, "page_no", None)

            if page_number is not None:
                page_numbers.add(page_number)

    return sorted(page_numbers)


def update_heading_path(headings: list, heading_state: dict) -> list:
    current_path = []

    for heading in headings or []:
        heading = heading.strip()

        match = re.match(
            r"^(\d+(?:\.\d+)*)(?:[.)])?\s+(.+)$",
            heading
        )

        if not match:
            heading_state.clear()
            heading_state["__root__"] = heading
            current_path = [heading]
            continue

        section_number = match.group(1)
        parts = section_number.split(".")

        for existing_number in list(heading_state.keys()):
            if existing_number == "__root__":
                del heading_state[existing_number]
                continue

            existing_parts = existing_number.split(".")

            is_parent = (
                len(existing_parts) < len(parts)
                and parts[:len(existing_parts)] == existing_parts
            )

            if not is_parent:
                del heading_state[existing_number]

        heading_state[section_number] = heading

        for depth in range(1, len(parts) + 1):
            parent_number = ".".join(parts[:depth])

            if parent_number in heading_state:
                current_path.append(heading_state[parent_number])

    return current_path


def attach_manifest_metadata(chunk: dict, manifest_entry: dict) -> dict:
    chunk.update({
        "doc_id": manifest_entry["doc_id"],
        "source_document": manifest_entry["source_document"],
        "source_path": manifest_entry["path"],
        "collection": manifest_entry["collection"],
        "access_roles": manifest_entry["access_roles"],
        "matter_id": manifest_entry["matter_id"],
        "format": manifest_entry["format"]
    })

    return chunk


def is_document_front_matter(chunk: dict) -> bool:
    text = chunk["text"].strip().lower()
    is_title_level = len(chunk["heading_path"]) == 1

    document_labels = {
        "team",
        "disputes team",
        "litigation teams"
    }

    return (
        is_title_level
        and (
            text in document_labels
            or text.startswith("distribution:")
        )
    )


def merge_incomplete_lead_ins(chunks: list) -> list:
    merged_chunks = []
    index = 0

    while index < len(chunks):
        current = chunks[index]

        if (
            current["text"].strip().lower() == "preferred wording:"
            and index + 1 < len(chunks)
        ):
            following = chunks[index + 1]

            if (
                current["heading_path"] == following["heading_path"]
                and current["chunk_type"] == following["chunk_type"]
            ):
                current["text"] = (
                    current["text"].strip()
                    + "\n\n"
                    + following["text"].strip()
                )

                current["page_numbers"] = sorted(set(
                    current["page_numbers"]
                    + following["page_numbers"]
                ))

                current["page_number"] = (
                    current["page_numbers"][0]
                    if len(current["page_numbers"]) == 1
                    else None
                )

                merged_chunks.append(current)
                index += 2
                continue

        merged_chunks.append(current)
        index += 1

    return merged_chunks


def build_document_chunks(document, manifest_entry: dict) -> list:
    hierarchical_chunks = list(CHUNKER.chunk(document))

    extracted_chunks = []
    heading_state = {}
    table_headings = {}
    text_number = 0

    for chunk in hierarchical_chunks:
        headings = chunk.meta.headings or []

        heading_path = update_heading_path(
            headings,
            heading_state
        )

        item_types = [
            get_item_type(item)
            for item in chunk.meta.doc_items
        ]

        for item in chunk.meta.doc_items:
            if get_item_type(item) == "table":
                table_headings[item.self_ref] = heading_path.copy()

        # Avoid indexing flattened versions of tables
        if "table" in item_types:
            continue

        text = chunk.text.strip()

        if not text:
            continue

        text_number += 1
        page_numbers = get_page_numbers(chunk.meta.doc_items)

        extracted_chunk = {
            "chunk_id": (
                f"{manifest_entry['doc_id']}:text:{text_number}"
            ),
            "chunk_type": "text",
            "section_heading": (
                headings[-1] if headings else None
            ),
            "heading_path": heading_path.copy(),
            "page_numbers": page_numbers,
            "page_number": (
                page_numbers[0] if len(page_numbers) == 1 else None
            ),
            "text": text
        }

        attach_manifest_metadata(extracted_chunk, manifest_entry)
        extracted_chunks.append(extracted_chunk)

    # Extract original tables as separate Markdown chunks
    for table_number, table in enumerate(document.tables, start=1):
        table_text = table.export_to_markdown(doc=document).strip()

        if not table_text:
            continue

        table_ref = f"#/tables/{table_number - 1}"

        heading_path = table_headings.get(
            table_ref,
            ["Unlabelled table"]
        )

        page_numbers = get_page_numbers([table])

        extracted_chunk = {
            "chunk_id": (
                f"{manifest_entry['doc_id']}:table:{table_number}"
            ),
            "chunk_type": "table",
            "section_heading": (
                heading_path[-1] if heading_path else None
            ),
            "heading_path": heading_path,
            "page_numbers": page_numbers,
            "page_number": (
                page_numbers[0] if len(page_numbers) == 1 else None
            ),
            "text": table_text
        }

        attach_manifest_metadata(extracted_chunk, manifest_entry)
        extracted_chunks.append(extracted_chunk)

    # Preserve distribution notices as metadata
    document_notices = [
        chunk["text"].strip()
        for chunk in extracted_chunks
        if (
            len(chunk["heading_path"]) == 1
            and chunk["text"].strip().lower().startswith("distribution:")
        )
    ]

    # Remove standalone team labels and distribution notices
    extracted_chunks = [
        chunk for chunk in extracted_chunks
        if not (
            chunk["chunk_type"] == "text"
            and is_document_front_matter(chunk)
        )
    ]

    # Join incomplete lead-ins to the following content
    extracted_chunks = merge_incomplete_lead_ins(extracted_chunks)

    # Attach notices to remaining chunks
    for chunk in extracted_chunks:
        chunk["document_notices"] = document_notices

    return extracted_chunks


def get_manifest_entry(doc_id: str) -> dict:
    documents = load_manifest()

    for document in documents:
        if document["doc_id"] == doc_id:
            return document

    raise ValueError(
        f"Document ID not found in manifest: {doc_id}"
    )


def ingest_document(doc_id: str) -> list:
    manifest_entry = get_manifest_entry(doc_id)

    dataset_root = DATASET_DIR.resolve()

    file_path = (
        dataset_root / manifest_entry["path"]
    ).resolve()

    if not file_path.is_relative_to(dataset_root):
        raise ValueError(
            "Document path is outside the dataset directory"
        )

    if not file_path.is_file():
        raise FileNotFoundError(
            f"Document file not found: {file_path}"
        )

    document = read_document(file_path)

    return build_document_chunks(
        document,
        manifest_entry
    )
