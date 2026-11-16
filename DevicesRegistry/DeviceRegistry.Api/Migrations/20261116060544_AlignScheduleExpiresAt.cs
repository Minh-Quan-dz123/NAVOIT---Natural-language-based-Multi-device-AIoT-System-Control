using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace DeviceRegistry.Api.Migrations
{
    /// <inheritdoc />
    public partial class AlignScheduleExpiresAt : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "AcknowledgedAt",
                table: "Schedules");

            migrationBuilder.DropColumn(
                name: "CommandId",
                table: "Schedules");

            migrationBuilder.DropColumn(
                name: "SyncStatus",
                table: "Schedules");

            migrationBuilder.AddColumn<long>(
                name: "ExpiresAt",
                table: "Schedules",
                type: "bigint",
                nullable: false,
                defaultValue: 0L);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "ExpiresAt",
                table: "Schedules");

            migrationBuilder.AddColumn<DateTime>(
                name: "AcknowledgedAt",
                table: "Schedules",
                type: "timestamp with time zone",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "CommandId",
                table: "Schedules",
                type: "text",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "SyncStatus",
                table: "Schedules",
                type: "text",
                nullable: false,
                defaultValue: "");
        }
    }
}
