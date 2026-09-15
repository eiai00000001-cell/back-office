import { Route, Routes } from 'react-router-dom'
import HomePage from './pages/HomePage'
import InvoiceListPage from './pages/InvoiceListPage'
import InvoiceDetailPage from './pages/InvoiceDetailPage'
import QuoteListPage from './pages/QuoteListPage'
import QuoteDetailPage from './pages/QuoteDetailPage'
import ExpenseListPage from './pages/ExpenseListPage'
import ExpenseFormPage from './pages/ExpenseFormPage'
import ExpenseSummaryPage from './pages/ExpenseSummaryPage'
import ReceivableListPage from './pages/ReceivableListPage'
import ClientMasterPage from './pages/ClientMasterPage'
import SettingsPage from './pages/SettingsPage'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/invoices" element={<InvoiceListPage />} />
      <Route path="/invoices/:id" element={<InvoiceDetailPage />} />
      <Route path="/quotes" element={<QuoteListPage />} />
      <Route path="/quotes/:id" element={<QuoteDetailPage />} />
      <Route path="/expenses" element={<ExpenseListPage />} />
      <Route path="/expenses/summary" element={<ExpenseSummaryPage />} />
      <Route path="/expenses/:id" element={<ExpenseFormPage />} />
      <Route path="/receivables" element={<ReceivableListPage />} />
      <Route path="/clients" element={<ClientMasterPage />} />
      <Route path="/settings" element={<SettingsPage />} />
    </Routes>
  )
}
