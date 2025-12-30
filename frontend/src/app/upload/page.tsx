'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@clerk/nextjs'
import AuthWrapper from '@/components/auth/AuthWrapper'
import { api } from '@/lib/api'

export default function UploadPage() {
    const router = useRouter()
    const { getToken } = useAuth()
    const [file, setFile] = useState<File | null>(null)
    const [uploading, setUploading] = useState(false)
    const [statusMessage, setStatusMessage] = useState<string | null>(null)
    const [error, setError] = useState<string | null>(null)

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            const selectedFile = e.target.files[0]
            if (selectedFile.type !== 'application/pdf') {
                setError('Please select a PDF file')
                setFile(null)
                return
            }
            setFile(selectedFile)
            setError(null)
            setStatusMessage(null)
        }
    }

    const handleUpload = async () => {
        if (!file) {
            setError('Please select a file first')
            return
        }

        setUploading(true)
        setError(null)
        setStatusMessage('Getting secure token...')

        const formData = new FormData()
        formData.append('file', file)

        try {
            // Get fresh token and update localStorage for the interceptor
            const token = await getToken()
            if (token) {
                localStorage.setItem('clerk_token', token)
            }

            setStatusMessage('Uploading PDF...')
            await api.post('/pdf/upload', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                    ...(token ? { Authorization: `Bearer ${token}` } : {})
                },
            })

            setStatusMessage('File uploaded! Generating quiz...')

            // Generate quiz immediately
            const freshToken = await getToken()
            const quizRes = await api.post('/quiz/generate', {
                stake_id: undefined // Backend will auto-create if missing
            }, {
                headers: {
                    ...(freshToken ? { Authorization: `Bearer ${freshToken}` } : {})
                }
            });

            setStatusMessage('Quiz generated! Redirecting...')
            setTimeout(() => {
                router.push(`/quiz/${quizRes.data.quiz_id}`)
            }, 1000)
        } catch (err: any) {
            console.error('Upload/Generate error:', err)
            setStatusMessage(null)
            setError(err.response?.data?.detail || 'Failed to process. Please try again.')
        } finally {
            setUploading(false)
        }
    }

    return (
        <AuthWrapper requireAuth={true}>
            <div className="min-h-screen bg-gray-50 py-12">
                <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="bg-white shadow sm:rounded-lg">
                        <div className="px-4 py-5 sm:p-6">
                            <div className="mb-6">
                                <Link href="/dashboard" className="text-blue-600 hover:text-blue-800 text-sm font-medium">
                                    &larr; Back to Dashboard
                                </Link>
                            </div>

                            <h1 className="text-2xl font-bold text-gray-900 mb-6">
                                Upload Study Material
                            </h1>

                            <div className="space-y-6">
                                <div className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center">
                                    <div className="space-y-2">
                                        <svg
                                            className="mx-auto h-12 w-12 text-gray-400"
                                            stroke="currentColor"
                                            fill="none"
                                            viewBox="0 0 48 48"
                                            aria-hidden="true"
                                        >
                                            <path
                                                d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                                                strokeWidth={2}
                                                strokeLinecap="round"
                                                strokeLinejoin="round"
                                            />
                                        </svg>
                                        <div className="text-sm text-gray-600">
                                            <label
                                                htmlFor="file-upload"
                                                className="relative cursor-pointer bg-white rounded-md font-medium text-blue-600 hover:text-blue-500 focus-within:outline-none focus-within:ring-2 focus-within:ring-offset-2 focus-within:ring-blue-500"
                                            >
                                                <span>Upload a file</span>
                                                <input
                                                    id="file-upload"
                                                    name="file-upload"
                                                    type="file"
                                                    accept=".pdf"
                                                    className="sr-only"
                                                    onChange={handleFileChange}
                                                    disabled={uploading}
                                                />
                                            </label>
                                            <p className="pl-1">or drag and drop</p>
                                        </div>
                                        <p className="text-xs text-gray-500">
                                            PDF up to 50MB
                                        </p>
                                    </div>
                                </div>

                                {file && (
                                    <div className="bg-blue-50 p-4 rounded-md">
                                        <div className="flex">
                                            <div className="flex-shrink-0">
                                                <svg className="h-5 w-5 text-blue-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                                                    <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" clipRule="evenodd" />
                                                </svg>
                                            </div>
                                            <div className="ml-3">
                                                <h3 className="text-sm font-medium text-blue-800">
                                                    Selected file: {file.name}
                                                </h3>
                                                <p className="text-xs text-blue-600 mt-1">
                                                    {(file.size / 1024 / 1024).toFixed(2)} MB
                                                </p>
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {error && (
                                    <div className="bg-red-50 p-4 rounded-md">
                                        <div className="flex">
                                            <div className="ml-3">
                                                <h3 className="text-sm font-medium text-red-800">
                                                    Error
                                                </h3>
                                                <div className="mt-2 text-sm text-red-700">
                                                    <p>{error}</p>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {statusMessage && (
                                    <div className="bg-blue-50 p-4 rounded-md">
                                        <div className="flex">
                                            <div className="ml-3">
                                                <h3 className="text-sm font-medium text-blue-800">
                                                    Status
                                                </h3>
                                                <div className="mt-2 text-sm text-blue-700">
                                                    <p>{statusMessage}</p>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                )}

                                <div className="flex justify-end">
                                    <button
                                        type="button"
                                        onClick={handleUpload}
                                        disabled={!file || uploading}
                                        className={`inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 ${(!file || uploading) ? 'opacity-50 cursor-not-allowed' : ''
                                            }`}
                                    >
                                        {uploading ? 'Uploading...' : 'Upload PDF'}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </AuthWrapper>
    )
}
