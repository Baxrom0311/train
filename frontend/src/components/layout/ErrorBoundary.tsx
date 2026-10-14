import { Component, type ErrorInfo, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { useLocation } from 'react-router-dom'
import { AlertTriangle, RotateCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { reportError } from '@/lib/monitoring'

interface Props {
  children: ReactNode
  /** O'zgarsa (boshqa sahifaga o'tish) xato holati tiklanadi. */
  resetKey: string
}

interface State {
  error: Error | null
  resetKey: string
}

/** Sahifa render paytida yiqilsa — butun ilova oq ekranga aylanmaydi (CONTRACT.md §32.4). */
class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null, resetKey: this.props.resetKey }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { error }
  }

  static getDerivedStateFromProps(props: Props, state: State): Partial<State> | null {
    return props.resetKey !== state.resetKey ? { error: null, resetKey: props.resetKey } : null
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    reportError('render', error, info.componentStack ?? '')
  }

  render() {
    return this.state.error ? <Fallback /> : this.props.children
  }
}

function Fallback() {
  const { t } = useTranslation()
  return (
    <div className="mx-auto max-w-lg px-4 py-16">
      <Card className="animate-rise">
        <CardContent className="flex flex-col items-center gap-4 p-8 text-center">
          <span className="grid h-12 w-12 place-items-center rounded-2xl bg-destructive/12 text-destructive">
            <AlertTriangle className="h-6 w-6" />
          </span>
          <div className="space-y-1">
            <h1 className="text-xl font-bold">{t('crash.title')}</h1>
            <p className="text-sm text-muted-foreground">{t('crash.text')}</p>
          </div>
          <Button onClick={() => window.location.reload()}>
            <RotateCw className="h-4 w-4" /> {t('crash.reload')}
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}

export default function RouteErrorBoundary({ children }: { children: ReactNode }) {
  const { pathname } = useLocation()
  return <ErrorBoundary resetKey={pathname}>{children}</ErrorBoundary>
}
