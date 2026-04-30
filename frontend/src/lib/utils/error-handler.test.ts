import { describe, expect, it } from 'vitest'

import { getApiErrorKey } from './error-handler'

describe('getApiErrorKey', () => {
  it('maps referenced public source delete errors', () => {
    expect(
      getApiErrorKey(
        "Cannot delete public source 'Example': it is referenced by 1 notebook(s)."
      )
    ).toBe('apiErrors.sourceReferencedCannotDelete')
  })
})
