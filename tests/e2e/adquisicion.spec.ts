import { test, expect } from '@playwright/test'
import { readFileSync } from 'node:fs'

const password = process.env.POSCOSEGRAN_AUTH_LOCAL_PASSWORD || readFileSync('backend/.env', 'utf8').match(/^POSCOSEGRAN_AUTH_LOCAL_PASSWORD=(.+)$/m)![1].trim()

test('reglas: añadir, editar y retirar quedan en una propuesta simulable', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  await page.goto('/adquisicion')
  await page.getByLabel('Usuario local').fill('ingeniero')
  await page.getByLabel('Contraseña', { exact: true }).fill(password)
  await page.getByRole('button', { name: 'Entrar', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Mantener la base de conocimiento' })).toBeVisible()

  await page.getByRole('button', { name: 'Añadir nueva regla' }).click()
  const editor = page.locator('section.panel').filter({ has: page.getByRole('heading', { name: /Editor de regla/ }) })
  await expect(editor).toContainText('R53')
  await editor.locator('.condicion-row select').nth(1).selectOption('humedad_grano')
  await editor.getByPlaceholder('Valor / umbral').fill('20')
  await editor.getByLabel('Hallazgo (hecho deducido)').fill('HUMEDAD_PRUEBA_ADQUISICION')
  await editor.getByLabel('Mensaje explicativo').fill('Revisar humedad del grano antes del almacenamiento.')
  await editor.getByLabel('Antecedente documentado').fill('Humedad del grano mayor a 20 por ciento.')
  await editor.getByLabel('Consecuente documentado').fill('Humedad alta detectada.')
  await editor.getByLabel('Acción recomendada').fill('Realizar inspección técnica.')
  await editor.getByLabel('Fundamento y referencias').fill('Regla de prueba para verificar el módulo de adquisición.')
  await editor.getByRole('button', { name: 'Aplicar cambio a la propuesta' }).click()
  await expect(editor).not.toBeVisible()

  await page.getByPlaceholder('Buscar regla por ID, nombre o etapa').fill('R53')
  await page.getByRole('button', { name: 'Editar' }).click()
  await editor.getByLabel('Mensaje explicativo').fill('Mensaje editado de la nueva regla.')
  await editor.getByRole('button', { name: 'Aplicar cambio a la propuesta' }).click()
  await page.getByPlaceholder('Buscar regla por ID, nombre o etapa').fill('R52')
  await page.getByRole('button', { name: 'Retirar' }).click()
  await expect(page.getByText('Retiro pendiente')).toBeVisible()
  await page.getByLabel('Motivo del cambio (obligatorio)').fill('Prueba de alta, edición y retiro de reglas')
  await page.getByRole('button', { name: 'Simular impacto' }).click()
  await expect(page.getByText(/Propuesta válida/)).toBeVisible({ timeout: 30000 })
  await expect(page.getByText('Nueva: R53')).toBeVisible()
  await expect(page.getByText('Retirada: R52')).toBeVisible()
  expect(errors).toEqual([])
})
