#!/usr/bin/env Rscript
# Historical numerical reconstruction, not a validated donor-level disease finding.
# Source inputs, mapping version and assumptions are frozen in the prospective plan.
args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 5L) {
  stop('Usage: expression.txt.gz sample_selection.csv mapping.csv output_dir accession')
}
if (!requireNamespace('limma', quietly = TRUE)) stop('limma is not installed')
if (as.character(packageVersion('limma')) != '3.56.2') {
  stop('This checkpoint requires exact limma3.56.2; version changes are separate variants')
}
expression_path <- args[[1L]]
samples_path <- args[[2L]]
mapping_path <- args[[3L]]
out <- args[[4L]]
accession <- args[[5L]]
if (accession != 'GSE132903') stop('Only the prospectively frozen GSE132903 pilot is enabled')
dir.create(out, showWarnings = FALSE, recursive = TRUE)
inputs <- read.csv(samples_path, stringsAsFactors = FALSE, check.names = FALSE)
selected <- inputs[inputs$dataset == accession & tolower(inputs$paper_group_eligible) == 'true', ]
if (nrow(selected) != 195L || anyDuplicated(selected$sample_accession)) stop('Unexpected pilot sample selection')
if (sum(selected$diagnosis == "Alzheimer's disease") != 97L || sum(selected$diagnosis == 'control') != 98L) {
  stop('Pilot AD/control counts differ from frozen plan')
}
con <- gzfile(expression_path, open = 'rt')
found <- FALSE
repeat {
  line <- readLines(con, n = 1L, warn = FALSE)
  if (!length(line)) break
  if (identical(line, '!series_matrix_table_begin')) {found <- TRUE; break}
}
if (!found) {close(con); stop('Matrix begin marker missing')}
tab <- read.delim(con, header = TRUE, nrows = 42179L, row.names = 1L,
                  check.names = FALSE, stringsAsFactors = FALSE, comment.char = '')
end <- readLines(con, n = 1L, warn = FALSE)
close(con)
if (!length(end) || end[[1L]] != '!series_matrix_table_end') stop('Unexpected matrix row count/end marker')
if (nrow(tab) != 42179L || anyDuplicated(rownames(tab))) stop('Unexpected/duplicate matrix features')
if (!all(selected$sample_accession %in% colnames(tab))) stop('Selected sample absent from matrix')
expr <- as.matrix(tab[, selected$sample_accession, drop = FALSE])
storage.mode(expr) <- 'double'
if (any(!is.finite(expr))) stop('Nonfinite expression values; missingness handling is not specified')
group <- factor(ifelse(selected$diagnosis == 'control', 'control', 'AD'), levels = c('control', 'AD'))
design <- model.matrix(~0 + group)
colnames(design) <- c('control', 'AD')
fit <- limma::lmFit(expr, design)
fit <- limma::contrasts.fit(fit, limma::makeContrasts(AD - control, levels = design))
fit <- limma::eBayes(fit, trend = FALSE, robust = FALSE)
results <- limma::topTable(fit, number = Inf, adjust.method = 'BH', sort.by = 'none')
results$feature_id <- rownames(results)
mapping <- read.csv(mapping_path, stringsAsFactors = FALSE, check.names = FALSE)
if (anyDuplicated(mapping$feature_id)) stop('Mapping contains duplicate feature IDs')
results$gene_symbol <- mapping$unique_symbol[match(results$feature_id, mapping$feature_id)]
results$mapping_status <- mapping$status[match(results$feature_id, mapping$feature_id)]
write.csv(results, file.path(out, 'probe_results.csv'), row.names = FALSE)
genes <- results[!is.na(results$gene_symbol) & nzchar(results$gene_symbol), ]
genes <- genes[order(genes$adj.P.Val, genes$P.Value, genes$feature_id), ]
genes <- genes[!duplicated(genes$gene_symbol), ]
write.csv(genes, file.path(out, 'gene_results.csv'), row.names = FALSE)
de <- genes[!is.na(genes$adj.P.Val) & genes$adj.P.Val < 0.05, ]
write.csv(de, file.path(out, 'significant_genes.csv'), row.names = FALSE)
summary <- data.frame(
  accession = accession, arrays = ncol(expr), AD_arrays = sum(group == 'AD'),
  control_arrays = sum(group == 'control'), tested_probes = nrow(results),
  mapped_single_symbol_probes = sum(!is.na(results$gene_symbol) & nzchar(results$gene_symbol)),
  unique_mapped_genes = nrow(genes), significant_probes_BH005 = sum(results$adj.P.Val < 0.05, na.rm = TRUE),
  significant_genes_BH005 = nrow(de), up_genes = sum(de$logFC > 0), down_genes = sum(de$logFC < 0),
  published_gene_count = 11773L, difference_from_published_count = nrow(de) - 11773L,
  limma_version = as.character(packageVersion('limma')),
  interpretation = 'R0 historical reconstruction assumptions; no corrected variant or classifier run')
write.csv(summary, file.path(out, 'checkpoint_summary.csv'), row.names = FALSE)
capture.output(sessionInfo(), file = file.path(out, 'sessionInfo.txt'))
write.csv(data.frame(sample_accession = selected$sample_accession, group = as.character(group)),
          file.path(out, 'included_samples.csv'), row.names = FALSE)
print(summary)
