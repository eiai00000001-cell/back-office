import { describe, expect, it } from 'vitest'
import { extractErrorMessage } from '../client'

describe('extractErrorMessage', () => {
  it('returns the detail string as-is when detail is a string', () => {
    const error = { response: { data: { detail: '名称を入力してください' } } }
    expect(extractErrorMessage(error)).toBe('名称を入力してください')
  })

  it('falls back to the first message when detail is FastAPI-style array (defense in depth)', () => {
    const error = {
      response: {
        data: {
          detail: [{ type: 'string_too_short', loc: ['body', 'name'], msg: 'String should have at least 1 character' }],
        },
      },
    }
    expect(extractErrorMessage(error)).toBe('String should have at least 1 character')
  })

  it('returns the fallback message when the array has no usable msg', () => {
    const error = { response: { data: { detail: [{}] } } }
    expect(extractErrorMessage(error, 'デフォルトエラー')).toBe('デフォルトエラー')
  })

  it('returns the fallback message when detail is missing', () => {
    const error = { response: { data: {} } }
    expect(extractErrorMessage(error, 'デフォルトエラー')).toBe('デフォルトエラー')
  })

  it('returns the default fallback message when error is not axios-shaped', () => {
    expect(extractErrorMessage(new Error('network error'))).toBe(
      '処理に失敗しました。しばらくしてから再度お試しください'
    )
  })
})
