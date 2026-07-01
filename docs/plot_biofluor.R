suppressPackageStartupMessages({library(ggplot2); library(dplyr); library(patchwork); library(scales)})
root <- '/work/BioFluor-GFP-2026'
data_dir <- file.path(root,'results','analysis_data')
out_dir <- file.path(root,'docs','figures')
dir.create(out_dir, recursive=TRUE, showWarnings=FALSE)
d <- read.csv(file.path(data_dir,'candidates.csv'), stringsAsFactors=FALSE)
iden <- read.csv(file.path(data_dir,'identity.csv'), stringsAsFactors=FALSE)
stage_levels <- c('Initial','Local R1','Local R2','Local R3')
d$stage <- factor(d$stage, levels=stage_levels)
classic <- theme_minimal(base_size=13) + theme(plot.title=element_text(face='bold', size=17, color='#17322b'), plot.subtitle=element_text(color='#5b6b64'), panel.grid.minor=element_blank())

best <- d %>% group_by(stage) %>% summarise(best=max(score), ptm=max(ptm), chromo=max(chromo), .groups='drop')
p1 <- ggplot(best, aes(stage, best, group=1)) + geom_line(color='#1f5c4d', linewidth=1.3) + geom_point(size=4, color='#d6a83a') + geom_text(aes(label=sprintf('%.4f', best)), vjust=-1, size=4) + labs(title='ＡＵＲＯＲＡ iterative score trajectory', subtitle='Independent amacGFP-derived route improves from 0.8008 to 0.9291', x=NULL, y='Top sort_score') + ylim(0.78,0.94) + classic

ggsave(file.path(out_dir,'01_score_trajectory.png'), p1, width=9, height=5.5, dpi=220)

p2 <- ggplot(d, aes(ptm, chromo, color=score, shape=stage)) + geom_point(size=3.2, alpha=.88) + scale_color_viridis_c(option='C') + scale_x_continuous(limits=c(0.65,0.93)) + scale_y_continuous(limits=c(0.65,0.97)) + labs(title='pTM × chromophore pLDDT frontier', subtitle='Local R2 moves the independent route into the upper-right frontier', x='pTM', y='Chromophore pLDDT', color='score') + classic

ggsave(file.path(out_dir,'02_ptm_chromo_frontier.png'), p2, width=8.5, height=6.5, dpi=220)

p3 <- ggplot(d, aes(stage, score, fill=stage)) + geom_boxplot(width=.45, alpha=.65, outlier.shape=NA) + geom_jitter(width=.08, size=2, alpha=.55) + guides(fill='none') + labs(title='Top6 score distribution by stage', subtitle='R2 has the strongest Top1 and median among tested local refinements', x=NULL, y='sort_score') + classic

ggsave(file.path(out_dir,'03_stage_distribution.png'), p3, width=9, height=5.8, dpi=220)

iden$seq_i <- factor(iden$seq_i, levels=paste0('#',1:6)); iden$seq_j <- factor(iden$seq_j, levels=rev(paste0('#',1:6)))
p4 <- ggplot(iden, aes(seq_i, seq_j, fill=identity)) + geom_tile(color='white') + geom_text(aes(label=sprintf('%.0f%%', identity*100)), size=3.5) + scale_fill_viridis_c(option='B', limits=c(0,1)) + labs(title='Local R2 Top6 sequence identity matrix', subtitle='Final set remains non-identical while sharing the same independent amacGFP lineage', x=NULL, y=NULL, fill='identity') + classic

ggsave(file.path(out_dir,'04_identity_matrix.png'), p4, width=7, height=6, dpi=220)

combo <- (p1 | p2) / (p3 | p4)
ggsave(file.path(out_dir,'00_biofluor_dashboard.png'), combo, width=16, height=11, dpi=190)

html <- paste0('<!doctype html><html><head><meta charset="utf-8"><title>ＡＵＲＯＲＡ analysis figures</title><style>body{font-family:Arial,sans-serif;background:#111;color:#eee;margin:32px}img{max-width:100%;background:#fff;border-radius:12px;margin:18px 0}h1{color:#d6a83a}</style></head><body><h1>ＡＵＲＯＲＡ GFP Design — Analysis Figures</h1><p>Current recommended submission: Local R2 Top6, Top1 sort_score=0.9291.</p>', paste0('<h2>',c('Dashboard','Score trajectory','pTM × chromophore pLDDT','Stage distribution','Identity matrix'),'</h2><img src="figures/',c('00_biofluor_dashboard.png','01_score_trajectory.png','02_ptm_chromo_frontier.png','03_stage_distribution.png','04_identity_matrix.png'),'">', collapse=''), '</body></html>')
writeLines(html, file.path(root,'docs','analysis_figures.html'))
cat('done\n')
