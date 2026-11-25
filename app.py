from pathlib import Path

import streamlit as st

from knowledge import (
    Claim,
    Document,
    Review,
    Scope,
    demo_documents,
    propose_fix,
    read_document,
    review_documents,
)


st.set_page_config(page_title="KnowledgeGuard", layout="wide")

DEFAULT_QUESTION = (
    "What can I claim for my home office under the remote-work allowance in Germany?"
)

DEFAULT_STATE = {
    "documents": {},
    "before": None,
    "current": None,
    "review_settings": None,
    "last_edited": None,
}
for name, value in DEFAULT_STATE.items():
    if name not in st.session_state:
        st.session_state[name] = value


def set_workspace(documents: dict[str, Document]) -> None:
    st.session_state.update(
        documents=documents,
        before=None,
        current=None,
        review_settings=None,
        last_edited=None,
    )


def source(claim: Claim) -> None:
    passage = claim.passage
    version = " · corrected working copy" if passage.edited else ""
    st.text(f"{passage.filename} · {passage.location}{version}")
    st.code(claim.quote, language=None)


def answer_card(title: str, review: Review) -> None:
    with st.container(border=True):
        st.subheader(title)
        if review.answer is None:
            st.info("The assistant found no matching passage for this question.")
            return

        st.metric("Assistant answer", review.answer.raw_amount)
        if review.reference is None:
            st.info("No authoritative value to compare against.")
        elif review.answer.amount == review.reference.amount:
            st.success("Matches the authoritative policy")
        else:
            st.error(f"Expected {review.reference.raw_amount} from the authoritative policy")

        st.caption("Cited source")
        source(review.answer)


with st.sidebar:
    st.header("Workspace")
    if st.button("Load sample workspace"):
        set_workspace(demo_documents())
        for key in ("authority", "topic", "audience", "region", "cadence", "question"):
            st.session_state.pop(key, None)

    st.header("Extraction mode")
    mode = st.radio("Mode", ["Local demo", "Gemini"])
    model = ""
    api_key = ""
    if mode == "Gemini":
        api_key = st.text_input("Gemini API key", type="password").strip()
        model = st.text_input("Gemini model ID", "gemini-3.8-flash").strip()
        st.caption("Extracted document text is sent to Gemini when you run a review.")
    else:
        st.caption("Runs offline. Matches exact scope phrases and one amount per passage.")


st.title("KnowledgeGuard")
st.caption("Find conflicting policy values and verify the assistant’s answer after a fix.")

with st.expander("Upload documents", expanded=not bool(st.session_state.documents)):
    with st.form("upload_documents", clear_on_submit=True):
        uploads = st.file_uploader(
            "Add PDF, Markdown, or text files",
            type=["pdf", "md", "txt"],
            accept_multiple_files=True,
        )
        upload_clicked = st.form_submit_button("Add documents")

    if upload_clicked:
        if not uploads:
            st.warning("Choose at least one file.")
        else:
            try:
                updated_documents = dict(st.session_state.documents)
                for uploaded in uploads:
                    document = read_document(uploaded.name, uploaded.getvalue())
                    updated_documents[document.id] = document
                set_workspace(updated_documents)
                st.success(f"Added or replaced {len(uploads)} document(s).")
            except ValueError as error:
                st.error(str(error))

documents = st.session_state.documents
if not documents:
    st.info("Load the sample workspace from the sidebar or upload your own documents.")
    st.stop()

st.caption(f"{len(documents)} documents in this workspace")
with st.expander("Documents in this review"):
    for document in documents.values():
        marker = " · corrected working copy" if document.edited else ""
        st.text(f"{document.name}{marker}")

authority_id = st.selectbox(
    "Authoritative document",
    list(documents),
    format_func=lambda document_id: documents[document_id].name,
    key="authority",
    help="Choose the official source to use as the expected policy value.",
)

with st.expander("Policy scope", expanded=True):
    left, right = st.columns(2)
    with left:
        topic = st.text_input("Policy topic", "remote-work allowance", key="topic").strip()
        audience = st.text_input("Applies to", "employees", key="audience").strip()
    with right:
        region = st.text_input("Region", "Germany", key="region").strip()
        cadence = st.text_input("Frequency", "per year", key="cadence").strip()

question = st.text_input("Question to test", DEFAULT_QUESTION, key="question").strip()
scope = Scope(topic, audience, region, cadence)
settings = (scope, authority_id, question, mode, model)


def run_review(workspace: dict[str, Document]) -> Review:
    if mode == "Gemini" and not model:
        raise ValueError("Enter a Gemini model ID in the sidebar.")
    return review_documents(
        workspace, scope, authority_id, question, model=model, api_key=api_key
    )


if st.button("Run review", type="primary"):
    try:
        with st.spinner("Checking document claims and testing the assistant…"):
            result = run_review(documents)
        st.session_state.update(
            before=result,
            current=result,
            review_settings=settings,
            last_edited=None,
        )
    except ValueError as error:
        st.error(str(error))

current = st.session_state.current
if current is None:
    st.stop()
if settings != st.session_state.review_settings:
    st.info("The review settings changed. Run a fresh review to see updated results.")
    st.stop()

before = st.session_state.before
last_edited = st.session_state.last_edited

st.divider()
st.header("Review results")
first, second, third = st.columns(3)
first.metric("Matching claims", current.claim_count)
second.metric(
    "Conflicting passages",
    len(current.conflicts) if current.reference else "Needs review",
)
third.metric(
    "Authoritative value",
    current.reference.raw_amount if current.reference else "Unknown",
)

if current.note:
    st.warning(current.note)
elif not current.conflicts:
    st.success("No same-currency conflicts found among the matched claims.")

if last_edited:
    left, right = st.columns(2)
    with left:
        answer_card("Before the fix", before)
    with right:
        answer_card("After the fix", current)
else:
    answer_card("Assistant preview", current)

if current.reference is not None:
    with st.expander("Authoritative evidence"):
        source(current.reference)

if current.conflicts and current.reference is not None:
    st.header("Suggested fixes")
    for number, stale in enumerate(current.conflicts, start=1):
        document = documents[stale.passage.document_id]
        with st.expander(
            f"{document.name} · {stale.raw_amount} instead of {current.reference.raw_amount}",
            expanded=number == 1,
        ):
            source(stale)
            corrected, diff = propose_fix(document, stale, current.reference)
            st.code(diff, language="diff")
            if st.button(
                "Apply fix and retest",
                key=f"fix-{stale.passage.id}-{stale.start}",
            ):
                candidate = dict(documents)
                candidate[corrected.id] = corrected
                try:
                    with st.spinner("Retesting the same assistant question…"):
                        retest = run_review(candidate)
                except ValueError as error:
                    st.error(str(error))
                else:
                    st.session_state.update(
                        documents=candidate,
                        current=retest,
                        last_edited=corrected.id,
                    )
                    st.rerun()

if last_edited:
    corrected = documents[last_edited]
    st.download_button(
        "Download corrected text",
        data=corrected.as_text(),
        file_name=f"{Path(corrected.name).stem}-corrected.txt",
        mime="text/plain",
    )