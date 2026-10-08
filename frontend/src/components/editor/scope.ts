// Muharrir kimniki (CONTRACT.md §16 admin, §26 kompaniya): API va sahifa manzili, cheklovlar.
import { createContext, useContext } from 'react'

export interface EditorScope {
  /** API prefiksi ham, sahifa manzili ham — ikkalasi bir xil. */
  base: '/admin/scenarios' | '/company/scenarios'
  /** §26.1: `company_name` — kompaniyaning o'zi, muharrirda o'zgarmaydi. */
  company: boolean
  maxDays: number
}

export const ADMIN_SCOPE: EditorScope = { base: '/admin/scenarios', company: false, maxDays: 10 }
export const COMPANY_SCOPE: EditorScope = { base: '/company/scenarios', company: true, maxDays: 5 }

export const EditorScopeContext = createContext<EditorScope>(ADMIN_SCOPE)
export const useEditorScope = () => useContext(EditorScopeContext)
