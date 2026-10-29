export function workflowPanel(status: string): string {
  if (status === 'WAIT_PARALLEL_WORKPAPER') return 'operationWorkpaper'
  if (['WAIT_OWNER_SIGNOFF_UPLOAD', 'SIGNOFF_REVIEWING'].includes(status)) return 'signoff'
  if (['THIRD_APPROVED_WAIT_OWNER_CONFIRM_SEND', 'WAIT_OWNER_EXTERNAL_AUDIT_CONFIRM'].includes(status)) return 'externalAuditConfirm'
  if (status.startsWith('WAIT_EXTERNAL_') || status.startsWith('EXTERNAL_')) return 'externalReview'
  return ''
}

export function entryPanel(panel: string, status: string): string {
  // A stale external-review todo link must not reopen a completed step.
  if (['externalAuditConfirm', 'externalReview'].includes(panel) &&
      ['WAIT_OWNER_SIGNOFF_UPLOAD', 'SIGNOFF_REVIEWING', 'WAIT_PARALLEL_WORKPAPER'].includes(status)) return workflowPanel(status)
  return panel
}

export function currentTodoLabel(specific: string, currentStep: string, panelLabel: string): string {
  return specific || currentStep || panelLabel
}
