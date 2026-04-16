export const ROLE_CODES = [
  'ADMIN',
  'SALES',
  'PROJECT_LEADER',
  'PROJECT_MEMBER',
  'FIRST_REVIEWER',
  'SECOND_REVIEWER',
  'THIRD_REVIEWER',
  'PRINT_ROOM',
  'FINANCE',
  'ARCHIVE_MANAGER'
] as const

export type RoleCode = (typeof ROLE_CODES)[number]
