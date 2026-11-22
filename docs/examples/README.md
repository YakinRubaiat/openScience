# Examples

End-to-end workflows that chain multiple specialist agents. Each example can
be run against a local install or the Docker stack (see
[Getting Started](../getting-started.md)).

| Example | Domain | Agents used |
|---------|--------|-------------|
| [RNASeq Analysis](rnaseq-analysis.md) | Bulk RNA-seq | qc_analyzer, deseq2_specialist, gsea_analyzer, publication_formatter |
| [Single-Cell Workflow](single-cell.md) | Single-cell | qc_analyzer, scanpy_specialist, matplotlib_stylist, methods_writer |
| [Literature Review Automation](literature-review.md) | Literature | pubmed_search, lit_summarizer, systematic_review, citation_manager |

All examples follow the same shape:

```python
from openscience import ScienceSession

session = ScienceSession()
session.load_data("<your data>")
result = session.analyze("<task description>")
session.visualize(result, output="figures/")
print(session.write_methods(result))
```

> Every figure and manuscript section produced by these examples carries a
> full provenance graph — see [API Reference](../api.md#artifacts).
