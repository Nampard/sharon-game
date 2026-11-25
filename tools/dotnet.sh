#!/usr/bin/env bash
# 프로젝트 폴더 안에 설치한 .NET SDK를 쓰는 래퍼.
# SDK(.dotnet), NuGet 패키지(.nuget), CLI 설정(.dotnet-home)이 모두 이 프로젝트 안에만 생기고,
# .NET CLI의 Microsoft 사용 통계 전송은 끈다.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export DOTNET_ROOT="$ROOT/.dotnet"
export DOTNET_CLI_HOME="$ROOT/.dotnet-home"
export NUGET_PACKAGES="$ROOT/.nuget/packages"
export DOTNET_CLI_TELEMETRY_OPTOUT=1
export DOTNET_NOLOGO=1
export DOTNET_SKIP_FIRST_TIME_EXPERIENCE=1
exec "$DOTNET_ROOT/dotnet" "$@"
