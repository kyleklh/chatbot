import { Component } from 'react';

export default class MarkdownBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }
  static getDerivedStateFromError(error) {
    return { error };
  }
  componentDidCatch(error, info) {
    if (typeof console !== 'undefined' && console.error) {
      console.error('[MarkdownBoundary]', error, info?.componentStack?.slice(0, 400));
    }
  }
  componentDidUpdate(prevProps) {
    if (prevProps.resetKey !== this.props.resetKey && this.state.error) {
      this.setState({ error: null });
    }
  }
  render() {
    if (this.state.error) {
      return (
        <pre className="whitespace-pre-wrap break-words text-[14px] leading-relaxed text-zinc-800 font-sans">
          {this.props.fallbackText || ''}
        </pre>
      );
    }
    return this.props.children;
  }
}
